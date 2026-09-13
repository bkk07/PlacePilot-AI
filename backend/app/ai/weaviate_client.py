# Weaviate connection + DocumentChunk collection management (v4 client).

import logging

import weaviate
import weaviate.classes.config as wvc_config

from app.core.config import settings

logger = logging.getLogger("rag.weaviate")

COLLECTION_NAME = "DocumentChunk"

# Extra properties for corpus lifecycle management (added alongside the original
# schema; older collections without them keep working for search/ingest).
_MANIFEST_PROPERTIES = [
    wvc_config.Property(name="content_hash", data_type=wvc_config.DataType.TEXT),
    wvc_config.Property(name="embedding_model", data_type=wvc_config.DataType.TEXT),
]


def get_client() -> weaviate.WeaviateClient:
    host, port = _parse_url(settings.WEAVIATE_URL)
    client = weaviate.connect_to_local(host=host, port=port, grpc_port=settings.WEAVIATE_GRPC_PORT)
    _ensure_collection(client)
    return client


def _parse_url(url: str) -> tuple[str, int]:
    from urllib.parse import urlparse

    parsed = urlparse(url if "://" in url else f"http://{url}")
    return parsed.hostname or "localhost", parsed.port or 8080


def _ensure_collection(client: weaviate.WeaviateClient) -> None:
    if client.collections.exists(COLLECTION_NAME):
        _ensure_manifest_properties(client)
        return
    client.collections.create(
        COLLECTION_NAME,
        vector_config=wvc_config.Configure.Vectors.self_provided(),
        properties=[
            wvc_config.Property(name="text", data_type=wvc_config.DataType.TEXT),
            wvc_config.Property(name="document_id", data_type=wvc_config.DataType.TEXT),
            wvc_config.Property(name="company", data_type=wvc_config.DataType.TEXT),
            wvc_config.Property(name="year", data_type=wvc_config.DataType.INT),
            wvc_config.Property(name="document_type", data_type=wvc_config.DataType.TEXT),
            wvc_config.Property(name="role", data_type=wvc_config.DataType.TEXT),
            wvc_config.Property(name="source", data_type=wvc_config.DataType.TEXT),
            wvc_config.Property(name="page_number", data_type=wvc_config.DataType.INT),
            wvc_config.Property(name="content_hash", data_type=wvc_config.DataType.TEXT),
            wvc_config.Property(name="embedding_model", data_type=wvc_config.DataType.TEXT),
        ],
    )


def _ensure_manifest_properties(client: weaviate.WeaviateClient) -> None:
    """Add lifecycle properties to collections created before they existed."""
    try:
        collection = client.collections.get(COLLECTION_NAME)
        config = collection.config.get()
        existing = {p.name for p in config.properties}
        for prop in _MANIFEST_PROPERTIES:
            if prop.name not in existing:
                collection.config.add_property(prop)
                logger.info("added property %s to existing collection", prop.name)
    except Exception as exc:  # schema migration is best-effort; search still works
        logger.warning("could not ensure manifest properties: %s", exc)


def get_collection(client: weaviate.WeaviateClient):
    return client.collections.get(COLLECTION_NAME)


def delete_collection(client: weaviate.WeaviateClient) -> None:
    """Drop the whole collection (full re-ingest path)."""
    if client.collections.exists(COLLECTION_NAME):
        client.collections.delete(COLLECTION_NAME)
        logger.info("collection %s deleted", COLLECTION_NAME)


def delete_document_chunks(client: weaviate.WeaviateClient, document_id: str) -> int:
    """Delete all chunks of one document in one batch. Returns the number deleted."""
    from weaviate.classes.query import Filter

    collection = get_collection(client)
    result = collection.data.delete_many(
        Filter.by_property("document_id").equal(document_id)
    )
    count = result.successful or 0
    logger.info("deleted %d chunks for document %s", count, document_id)
    return count
