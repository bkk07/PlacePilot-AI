# Embeddings via local sentence-transformers (no API needed).
# The model import is lazy so RAG modules can be imported (and unit-tested)
# without pulling in torch.

from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    return model.encode(texts, normalize_embeddings=True).tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]