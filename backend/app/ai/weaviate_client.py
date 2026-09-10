# Weaviate connection + DocumentChunk collection management (v4 client).

import weaviate
import weaviate.classes.config as wvc_config

from app.core.config import settings

COLLECTION_NAME = "DocumentChunk"


def get_client() -> weaviate.WeaviateClient:
    host, port = _parse_url(settings.WEAVIATE_URL)
    client = weaviate.connect_to_local(host=host, port=port, grpc_port=50051)
    _ensure_collection(client)
    return client


def _parse_url(url: str) -> tuple[str, int]:
    from urllib.parse import urlparse

    parsed = urlparse(url if "://" in url else f"http://{url}")
    return parsed.hostname or "localhost", parsed.port or 8080


def _ensure_collection(client: weaviate.WeaviateClient) -> None:
    if client.collections.exists(COLLECTION_NAME):
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
        ],
    )


def get_collection(client: weaviate.WeaviateClient):
    return client.collections.get(COLLECTION_NAME)
