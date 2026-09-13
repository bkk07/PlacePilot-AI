# Retrieval quality layer: optional reranking + semantic query cache.
# Both features degrade gracefully — if the extra models/Redis are unavailable,
# retrieval returns the plain hybrid results (logged).

import hashlib
import json
import logging
import os

from app.core.config import settings

logger = logging.getLogger("rag.quality")


# ---------------------------------------------------------------------------
# Semantic cache: keyed by (normalized query, top_k, filters). Uses Redis when
# reachable (shared across processes), else disabled. Exact-match only.
# ---------------------------------------------------------------------------

def _cache_key(query: str, top_k: int, filters: dict | None) -> str:
    payload = json.dumps({"q": query.strip().lower(), "k": top_k, "f": filters or {}}, sort_keys=True)
    return "ragcache:" + hashlib.sha256(payload.encode()).hexdigest()


def _redis():
    try:
        import redis as _redis

        client = _redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception:
        return None


def cache_get(query: str, top_k: int, filters: dict | None):
    """Return cached chunk dicts for this exact query, or None on a miss."""
    key = _cache_key(query, top_k, filters)
    try:
        client = _redis()
        if client is not None:
            raw = client.get(key)
            if raw:
                return json.loads(raw)
    except Exception as exc:
        logger.warning("semantic cache read failed: %s", exc)
    return None


def cache_put(query: str, top_k: int, filters: dict | None, chunks: list[dict], ttl_s: int = 3600) -> None:
    key = _cache_key(query, top_k, filters)
    try:
        client = _redis()
        if client is not None:
            client.setex(key, ttl_s, json.dumps(chunks))
    except Exception as exc:
        logger.warning("semantic cache write failed: %s", exc)


# ---------------------------------------------------------------------------
# Reranking: cross-encoder re-scoring of hybrid candidates. Opt-in via env
# (RAG_RERANKER=1) since it loads a second transformer model into memory.
# Falls back to the original hybrid order when the model can't be loaded.
# ---------------------------------------------------------------------------

_reranker = None
_reranker_attempted = False


def get_reranker():
    global _reranker, _reranker_attempted
    if _reranker_attempted:
        return _reranker
    _reranker_attempted = True
    if os.getenv("RAG_RERANKER", "0") not in ("1", "true", "yes"):
        return None
    try:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        logger.info("reranker loaded")
    except Exception as exc:
        logger.warning("reranker unavailable (%s) — using hybrid order", exc)
        _reranker = None
    return _reranker


def rerank(query: str, chunks: list[dict], top_k: int) -> list[dict]:
    """Re-score chunks against the query with a cross-encoder; return top_k."""
    model = get_reranker()
    if model is None or not chunks:
        return chunks[:top_k]
    try:
        pairs = [(query, c["text"]) for c in chunks]
        scores = model.predict(pairs)
        for chunk, score in zip(chunks, scores):
            chunk["score"] = round(float(score), 4)
            chunk["reranked"] = True
        return sorted(chunks, key=lambda c: c["score"], reverse=True)[:top_k]
    except Exception as exc:
        logger.warning("reranking failed (%s) — keeping hybrid order", exc)
        return chunks[:top_k]
