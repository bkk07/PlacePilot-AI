# Retriever: hybrid (BM25+vector) + metadata filtering against Weaviate.
# Default = hybrid alpha 0.65; falls back to near_vector if hybrid unavailable.

from dataclasses import dataclass

from app.ai.embeddings import embed_query
from app.ai.weaviate_client import get_client, get_collection


@dataclass
class RetrievedChunk:
    text: str
    score: float
    document_id: str
    company: str
    document_type: str
    role: str
    source: str
    page_number: int
    year: int | None = None


def _build_filter(filters: dict | None):
    """Build Weaviate Filter from dict like {'company': 'TCS', 'document_type': 'job_description'}."""
    if not filters:
        return None
    try:
        from weaviate.classes.query import Filter
        conds = []
        for k, v in filters.items():
            if v is None or v == "":
                continue
            if isinstance(v, list):
                # OR across list values
                sub = Filter.by_property(k).equal(v[0])
                for val in v[1:]:
                    sub = sub | Filter.by_property(k).equal(val)
                conds.append(sub)
            else:
                conds.append(Filter.by_property(k).equal(v))
        if not conds:
            return None
        f = conds[0]
        for c in conds[1:]:
            f = f & c
        return f
    except Exception:
        return None


def retrieve(
    query: str,
    top_k: int = 5,
    min_score: float = 0.30,
    filters: dict | None = None,
    alpha: float = 0.65,
    use_hybrid: bool = True,
) -> list[RetrievedChunk]:
    """Hybrid BM25+vector + optional metadata filter. Falls back to near_vector."""
    client = get_client()
    try:
        collection = get_collection(client)
        vector = embed_query(query)
        weav_filter = _build_filter(filters)

        try:
            if use_hybrid:
                # hybrid: query (BM25) + vector, alpha balances them
                kwargs = dict(
                    query=query,
                    vector=vector,
                    alpha=alpha,
                    limit=top_k,
                    return_metadata=["score"],
                )
                if weav_filter is not None:
                    kwargs["filters"] = weav_filter
                response = collection.query.hybrid(**kwargs)
                meta_attr = "score"
            else:
                raise RuntimeError("force near_vector")
        except Exception:
            # fallback to pure vector if hybrid fails (e.g., older Weaviate)
            kwargs = dict(near_vector=vector, limit=top_k, return_metadata=["distance"])
            if weav_filter is not None:
                kwargs["filters"] = weav_filter
            response = collection.query.near_vector(**kwargs)
            meta_attr = "distance"

        results: list[RetrievedChunk] = []
        for obj in response.objects:
            md = obj.metadata
            if meta_attr == "score":
                score = float(getattr(md, "score", 0.0) or 0.0)
                # hybrid score is 0-1 already; normalize if needed
                if score == 0.0 and hasattr(md, "distance"):
                    score = 1.0 - float(md.distance or 1.0)
            else:
                distance = float(getattr(md, "distance", 1.0) or 1.0)
                score = 1.0 - distance
            if score < min_score:
                continue
            props = obj.properties
            results.append(
                RetrievedChunk(
                    text=props.get("text", ""),
                    score=round(float(score), 4),
                    document_id=props.get("document_id", ""),
                    company=props.get("company", ""),
                    document_type=props.get("document_type", ""),
                    role=props.get("role", ""),
                    source=props.get("source", ""),
                    page_number=props.get("page_number", 0),
                    year=props.get("year"),
                )
            )
        return results
    finally:
        client.close()
