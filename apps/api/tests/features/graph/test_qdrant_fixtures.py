"""Smoke tests to verify Qdrant test fixtures work correctly."""

import uuid

import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from app.features.graph.services.embedding_service import EmbeddingService


class TestQdrantClientFixture:
    """Verify qdrant_client fixture provides working client."""

    @pytest.mark.asyncio
    async def test_client_connects(self, qdrant_client: AsyncQdrantClient) -> None:
        """Test that client can connect and collection exists."""
        collections = await qdrant_client.get_collections()
        names = [c.name for c in collections.collections]
        assert "agent_memory_test" in names

    @pytest.mark.asyncio
    async def test_can_upsert_and_query(self, qdrant_client: AsyncQdrantClient) -> None:
        """Test basic upsert and query operations."""
        # Upsert a test point (ID must be UUID or integer)
        point_id = str(uuid.uuid4())
        await qdrant_client.upsert(
            collection_name="agent_memory_test",
            points=[
                PointStruct(
                    id=point_id,
                    vector=[0.1] * 768,
                    payload={"tenant_id": "test", "type": "semantic"},
                )
            ],
        )

        # Count should be 1
        count = await qdrant_client.count(collection_name="agent_memory_test")
        assert count.count == 1

    @pytest.mark.asyncio
    async def test_collection_is_isolated_per_test(
        self, qdrant_client: AsyncQdrantClient
    ) -> None:
        """Test that collection starts empty (isolated from other tests)."""
        count = await qdrant_client.count(collection_name="agent_memory_test")
        assert count.count == 0


class TestEmbeddingServiceFixture:
    """Verify embedding_service fixture provides working service."""

    @pytest.mark.asyncio
    async def test_embedding_dimension(
        self, embedding_service: EmbeddingService
    ) -> None:
        """Test that embeddings have correct dimension."""
        embedding = await embedding_service.embed_text(
            "test text",
            feature="graph",
            operation="semantic_memory_embed",
        )
        # Check dimension matches what the service is configured for
        assert len(embedding) == embedding_service.embedding_dim
