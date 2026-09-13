# Knowledge-server tool implementations: RAG-backed search over Weaviate.

from app.ai.companies import normalize_company
from app.ai.retrieval_quality import cache_get, cache_put, rerank
from app.ai.retriever import retrieve
from app.core.security import AuthContext
from app.schemas.mcp_tool_schemas import PolicyQueryInput

# Candidate pool is over-fetched by this factor before reranking trims to top_k.
OVERFETCH_FACTOR = 3


def search_policy_docs_impl(auth: AuthContext, inp: PolicyQueryInput) -> dict:
    """RAG retrieval over placement documents. Grounding happens in the retriever:
    nothing relevant -> empty results -> the agent declines instead of hallucinating.
    Optional company/document_type filters narrow the hybrid search. Results are
    cached per exact query and optionally reranked by a cross-encoder."""
    filters: dict = {}
    if inp.company:
        canonical = normalize_company(inp.company)
        if canonical:
            filters["company"] = canonical
        else:
            # Unknown company names must not silently become an unfiltered query.
            return {
                "chunks": [],
                "note": f"no documents indexed for company '{inp.company}'",
            }
    if inp.document_type:
        filters["document_type"] = inp.document_type.strip().lower()

    cached = cache_get(inp.query, inp.top_k, filters or None)
    if cached is not None:
        return {"chunks": cached, "cached": True}

    try:
        # Over-fetch candidates, then rerank down to the requested top_k.
        candidates = retrieve(
            inp.query,
            top_k=inp.top_k * OVERFETCH_FACTOR,
            filters=filters or None,
        )
    except ValueError as exc:
        # unsupported filter keys — fail closed instead of broadening the query
        return {"chunks": [], "error": str(exc)}

    chunk_dicts = [
        {
            "text": c.text,
            "source": c.source,
            "page_number": c.page_number,
            "company": c.company,
            "document_type": c.document_type,
            "score": c.score,
        }
        for c in candidates
    ]
    chunk_dicts = rerank(inp.query, chunk_dicts, inp.top_k)
    cache_put(inp.query, inp.top_k, filters or None, chunk_dicts)
    # strip internal score fields from the agent-facing payload
    for c in chunk_dicts:
        c.pop("score", None)
        c.pop("reranked", None)
    return {"chunks": chunk_dicts}
