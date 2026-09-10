# Knowledge-server tool implementations: RAG-backed search over Weaviate.

from app.ai.retriever import retrieve
from app.core.security import AuthContext
from app.schemas.mcp_tool_schemas import PolicyQueryInput


def search_policy_docs_impl(auth: AuthContext, inp: PolicyQueryInput) -> dict:
    """RAG retrieval over placement documents. Grounding happens in the retriever:
    nothing relevant -> empty results -> the agent declines instead of hallucinating."""
    chunks = retrieve(inp.query, top_k=3)
    return {
        "chunks": [
            {
                "text": c.text,
                "source": c.source,
                "page_number": c.page_number,
                "company": c.company,
                "document_type": c.document_type,
            }
            for c in chunks
        ]
    }
