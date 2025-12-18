"""Qdrant database initialization.

This module handles the creation and configuration of the agent_memory collection,
including all required payload indexes for efficient filtering.
"""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from app.core.settings import get_settings


async def init_qdrant_db(client: AsyncQdrantClient) -> None:
    """Initialize the Qdrant database with required collections and indexes.

    This function is idempotent - safe to call multiple times.
    It creates the agent_memory collection if it doesn't exist and
    ensures all required payload indexes are in place.

    Args:
        client: The AsyncQdrantClient instance to use.
    """
    settings = get_settings()
    collection_name = settings.vector_collection_name

    # Check if collection exists
    collections = await client.get_collections()
    collection_names = [c.name for c in collections.collections]

    if collection_name not in collection_names:
        # Create collection with configured vector parameters
        _ = await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dim,
                distance=Distance.COSINE,
            ),
        )

    # Create payload indexes for efficient filtering
    # Index creation is idempotent - calling on existing index is a no-op
    indexes_to_create = [
        ("tenant_id", PayloadSchemaType.KEYWORD),
        ("entity_id", PayloadSchemaType.KEYWORD),
        ("type", PayloadSchemaType.KEYWORD),
        ("fact_id", PayloadSchemaType.KEYWORD),
        ("verb", PayloadSchemaType.KEYWORD),
    ]

    for field_name, field_schema in indexes_to_create:
        try:
            _ = await client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_schema,
            )
        except Exception:
            # Index might already exist, which is fine
            pass
