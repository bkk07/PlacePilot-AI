# MCP client manager: the agent's connection to the three tool servers.
# Each server exposes tools that independently re-check authorization via the
# caller's JWT — the agent passes the student's token through, never its own trust.

import asyncio
import logging
import time

from langchain_mcp_adapters.client import MultiServerMCPClient

from app.core.config import settings
from app.core.observability import metrics

logger = logging.getLogger("agent.mcp_client")

# Server URLs come from settings (MCP_PLACEMENT_URL etc., with host/port defaults).
MCP_SERVERS = settings.mcp_server_urls()

# One shared client per process — creating a MultiServerMCPClient per call
# reconnects to all three servers every time (the churn P5 fixed).
_client: MultiServerMCPClient | None = None
_tools_cache: dict[str, object] = {}
_cache_loaded_at: float = 0.0
_refresh_lock = asyncio.Lock()

def _get_client() -> MultiServerMCPClient:
    global _client
    if _client is None:
        _client = MultiServerMCPClient(MCP_SERVERS)
    return _client


async def _fetch_catalog() -> dict[str, object]:
    """Fetch the tool catalog from all servers, warning on name collisions."""
    client = _get_client()
    mcp_tools = await client.get_tools()
    catalog: dict[str, object] = {}
    for t in mcp_tools:
        if t.name in catalog:
            logger.warning("MCP tool name collision: %s exposed by multiple servers", t.name)
            metrics.inc("mcp_tool_name_collisions")
        catalog[t.name] = t
    return catalog


async def _get_tools(force: bool = False) -> dict[str, object]:
    """Fetch (and cache) the tool catalog with a TTL; refresh under a lock so
    concurrent cold-starts don't double-fetch. A server restart mid-flight is
    recovered by call_tool's one-shot refresh on unknown tool names."""
    global _tools_cache, _cache_loaded_at
    now = time.monotonic()
    if not force and _tools_cache and (now - _cache_loaded_at) < settings.MCP_CATALOG_TTL_S:
        return _tools_cache
    async with _refresh_lock:
        if not force and _tools_cache and (time.monotonic() - _cache_loaded_at) < settings.MCP_CATALOG_TTL_S:
            return _tools_cache  # another coroutine just refreshed it
        _tools_cache = await _fetch_catalog()
        _cache_loaded_at = time.monotonic()
        return _tools_cache


def reset_client() -> None:
    """Drop the cached client/tools (used by tests and after server restarts)."""
    global _client, _tools_cache, _cache_loaded_at
    _client = None
    _tools_cache = {}
    _cache_loaded_at = 0.0


async def list_tools(token: str = "") -> list[dict]:
    """Fetch tool specs from all three servers; token reserved for future
    role-filtered catalogs (the servers re-check authz per call anyway)."""
    tools = await _get_tools()
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "args": _tool_args(t),
        }
        for t in tools.values()
    ]


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


def coerce_args(tool, args: dict) -> dict:
    """Coerce string LLM emissions to the schema's declared types (int/float/bool).
    The agent's ToolCallSpec.args is dict[str,str]; MCP tools expect real types."""
    schema = getattr(tool, "args_schema", None) or (tool.args if hasattr(tool, "args") else {})
    if not isinstance(schema, dict) or not schema.get("properties"):
        return args
    out = dict(args)
    for name, prop in schema.get("properties", {}).items():
        if name not in out:
            continue
        val, ptype = out[name], prop.get("type")
        if isinstance(val, str) and ptype in ("integer", "number"):
            try:
                out[name] = int(val) if ptype == "integer" else float(val)
            except ValueError:
                logger.warning("could not coerce arg %s=%r to %s — passing through", name, val, ptype)
        elif isinstance(val, str) and ptype == "boolean":
            out[name] = val.strip().lower() in ("1", "true", "yes")
    return out


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
    """Call one tool on its server with the caller's token for authz re-check.
    Applies: arg type coercion, per-call timeout, retry with backoff on
    transient transport errors, and a one-shot catalog refresh on unknown tools."""
    tools = await _get_tools()
    if tool_name not in tools:
        # maybe a server restarted with new tools — refresh once and retry
        try:
            tools = await _get_tools(force=True)
        except Exception as exc:
            logger.warning("catalog refresh failed: %s", exc)
            return {"error": f"unknown tool: {tool_name}"}
        if tool_name not in tools:
            return {"error": f"unknown tool: {tool_name}"}

    tool = tools[tool_name]
    payload = {**coerce_args(tool, args), "token": token}
    retries = max(0, settings.MCP_TOOL_RETRIES)
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with metrics.timed(f"mcp_call:{tool_name}"):
                result = await asyncio.wait_for(
                    tool.ainvoke(payload),
                    timeout=settings.MCP_TOOL_TIMEOUT_S,
                )
            return _normalize_result(result)
        except asyncio.TimeoutError:
            last_exc = TimeoutError(f"tool {tool_name} timed out after {settings.MCP_TOOL_TIMEOUT_S}s")
            metrics.inc(f"mcp_call_timeouts:{tool_name}")
            # timeouts count as transient — fall through to retry/backoff
        except Exception as exc:
            last_exc = exc
            # Authorization/validation errors come back as result dicts, not
            # exceptions — a raising exception is a transport-level problem.
            if attempt == retries:
                break
        if attempt < retries:
            await asyncio.sleep(min(0.5 * (2**attempt), 5.0))
    metrics.inc(f"mcp_call_failures:{tool_name}")
    logger.warning("tool call %s failed: %s", tool_name, last_exc)
    return {"error": f"tool {tool_name} unavailable: {last_exc}", "code": "transport_error"}
