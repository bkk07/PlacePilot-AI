# MCP client manager: the agent's connection to the three tool servers.
# Each server exposes tools that independently re-check authorization via the
# caller's JWT — the agent passes the student's token through, never its own trust.

import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient

MCP_SERVERS = {
    "placement": {"url": "http://127.0.0.1:8101/mcp", "transport": "streamable_http"},
    "student": {"url": "http://127.0.0.1:8102/mcp", "transport": "streamable_http"},
    "knowledge": {"url": "http://127.0.0.1:8103/mcp", "transport": "streamable_http"},
}


async def list_tools(token: str) -> list[dict]:
    """Fetch tool specs from all three servers, inject the JWT, return catalog entries."""
    client = MultiServerMCPClient(MCP_SERVERS)
    mcp_tools = await client.get_tools()
    tools = []
    for t in mcp_tools:
        tools.append(
            {
                "name": t.name,
                "description": t.description or "",
                "args": _tool_args(t),
            }
        )
    return tools


def _tool_args(tool) -> dict:
    """Best-effort extraction of arg names from the tool's input schema."""
    schema = getattr(tool, "args_schema", None) or (tool.args if hasattr(tool, "args") else {})
    if isinstance(schema, dict):
        props = schema.get("properties", {})
        return {name: prop.get("type", "string") for name, prop in props.items()}
    # Pydantic model
    if hasattr(schema, "model_json_schema"):
        props = schema.model_json_schema().get("properties", {})
        return {name: prop.get("type", "string") for name, prop in props.items()}
    return {}


def _normalize_result(result) -> dict:
    """Turn whatever the MCP adapter returns (dict, JSON string, or content-block
    list) into a plain dict for the agent's synthesis step."""
    import json

    if isinstance(result, dict):
        return result
    if isinstance(result, list):
        texts = []
        for block in result:
            if isinstance(block, dict):
                if "text" in block:
                    texts.append(block["text"])
                else:
                    texts.append(json.dumps(block, default=str))
            else:
                texts.append(str(block))
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except (TypeError, ValueError):
            return {"result": joined}
    if isinstance(result, str):
        try:
            return json.loads(result)
        except (TypeError, ValueError):
            return {"result": result}
    return {"result": result}


async def call_tool(tool_name: str, token: str, args: dict) -> dict:
    """Call one tool on its server with the caller's token for authz re-check."""
    client = MultiServerMCPClient(MCP_SERVERS)
    tools = {t.name: t for t in await client.get_tools()}
    if tool_name not in tools:
        return {"error": f"unknown tool: {tool_name}"}
    result = await tools[tool_name].ainvoke({**args, "token": token})
    return _normalize_result(result)
