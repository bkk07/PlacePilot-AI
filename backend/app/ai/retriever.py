# Retriever: embed query with the same model, near_vector search against Weaviate.

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


def retrieve(query: str, top_k: int = 5, min_score: float = 0.30) -> list[RetrievedChunk]:
    """Return top-k chunks above min_score, or an empty list if nothing is relevant."""
    client = get_client()
    try:
        collection = get_collection(client)
        vector = embed_query(query)
        response = collection.query.near_vector(
            near_vector=vector,
            limit=top_k,
            return_metadata=["distance"],
        )
        results: list[RetrievedChunk] = []
        for obj in response.objects:
            distance = obj.metadata.distance if obj.metadata else 1.0
            score = 1.0 - distance
            if score < min_score:
                continue
            props = obj.properties
            results.append(
                RetrievedChunk(
                    text=props["text"],
                    score=round(score, 4),
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
