"""Integration tests for AssimilateKnowledgeUseCaseImpl with vector memory.

This module provides integration tests for the AssimilateKnowledgeUseCaseImpl
combined with VectorRepository to verify that facts are vectorized during
the assimilation process.
"""

import uuid

import asyncpg
import pytest
from qdrant_client import AsyncQdrantClient

from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    IdentifierDto,
)
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.repositories.qdrant_repository import QdrantRepository
from app.features.graph.services.embedding_service import EmbeddingService
from app.features.graph.services.langchain_fact_extractor import LangChainFactExtractor
from app.features.graph.usecases.assimilate_knowledge_usecase import (
    AssimilateKnowledgeUseCaseImpl,
)
from tests.conftest import TEST_QDRANT_COLLECTION


@pytest.fixture
def age_repository(postgres_pool: asyncpg.Pool) -> AgeRepository:
    """Fixture to get an AgeRepository instance."""
    return AgeRepository(postgres_pool, graph_name="test_graph")


@pytest.fixture
def langchain_fact_extractor() -> LangChainFactExtractor:
    """LangChainFactExtractor instance for testing."""
    return LangChainFactExtractor()


@pytest.fixture
def vector_repository(
    qdrant_client: AsyncQdrantClient,
    embedding_service: EmbeddingService,
) -> QdrantRepository:
    """VectorRepository instance for testing."""
    return QdrantRepository(
        client=qdrant_client,
        embedding_service=embedding_service,
        tenant_id="test_tenant",
        collection_name=TEST_QDRANT_COLLECTION,
    )


@pytest.fixture
def assimilate_usecase_with_vectors(
    age_repository: AgeRepository,
    langchain_fact_extractor: LangChainFactExtractor,
    vector_repository: QdrantRepository,
) -> AssimilateKnowledgeUseCaseImpl:
    """AssimilateKnowledgeUseCaseImpl with vector repository for testing."""
    return AssimilateKnowledgeUseCaseImpl(
        graph_repository=age_repository,
        fact_extractor=langchain_fact_extractor,
        vector_repository=vector_repository,
    )


@pytest.fixture
def assimilate_usecase_without_vectors(
    age_repository: AgeRepository,
    langchain_fact_extractor: LangChainFactExtractor,
) -> AssimilateKnowledgeUseCaseImpl:
    """AssimilateKnowledgeUseCaseImpl without vector repository (backward compat)."""
    return AssimilateKnowledgeUseCaseImpl(
        graph_repository=age_repository,
        fact_extractor=langchain_fact_extractor,
        # No vector_repository - backward compatibility
    )


@pytest.fixture
def test_identifier() -> IdentifierDto:
    """Test identifier for integration testing."""
    return IdentifierDto(
        value=f"test.vectors.{uuid.uuid4()}@example.com",
        type="email",
    )


class TestAssimilateKnowledgeWithVectors:
    """Integration tests for assimilation with semantic vectorization."""

    @pytest.mark.asyncio
    async def test_assimilate_creates_semantic_vectors(
        self,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        vector_repository: QdrantRepository,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that assimilating knowledge also creates semantic vectors."""
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Paris and work as a Software Engineer.",
        )

        # Act
        result = await assimilate_usecase_with_vectors.execute(request)

        # Assert: Facts were created
        assert len(result.assimilated_facts) > 0

        # Assert: Vectors were created (one per fact)
        search_results = await vector_repository.search_semantic_memory(
            entity_id=result.entity.id,
            query_text="Where does this person live?",
            top_k=10,
        )

        # Should find at least one fact
        assert len(search_results) > 0

    @pytest.mark.asyncio
    async def test_assimilate_creates_vector_for_each_fact(
        self,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        vector_repository: QdrantRepository,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that each assimilated fact gets a corresponding vector."""
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Tokyo. I work as a Data Scientist. I enjoy playing tennis.",
        )

        # Act
        result = await assimilate_usecase_with_vectors.execute(request)

        # Assert: Multiple facts were created
        assert len(result.assimilated_facts) > 1

        # Search for all facts using a generic query
        search_results = await vector_repository.search_semantic_memory(
            entity_id=result.entity.id,
            query_text="Tell me about this person",
            top_k=20,
        )

        # Should have same number of vectors as assimilated facts
        assert len(search_results) == len(result.assimilated_facts)

    @pytest.mark.asyncio
    async def test_vectors_point_to_real_graph_data(
        self,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        vector_repository: QdrantRepository,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that vector search results point to real graph data."""
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in New York City.",
        )

        # Act
        result = await assimilate_usecase_with_vectors.execute(request)

        # Get vector search results
        search_results = await vector_repository.search_semantic_memory(
            entity_id=result.entity.id,
            query_text="Where does this person live?",
            top_k=5,
        )

        # Assert: Vector results match graph facts
        assert len(search_results) > 0
        vector_fact_ids = {r.fact_id for r in search_results}
        graph_fact_ids = {f.fact.fact_id for f in result.assimilated_facts}

        # All vector fact_ids should exist in the graph
        assert vector_fact_ids.issubset(graph_fact_ids)

    @pytest.mark.asyncio
    async def test_semantic_search_returns_relevant_facts(
        self,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        vector_repository: QdrantRepository,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that semantic search returns relevant facts based on query."""
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in London. I work as a Doctor. I enjoy reading books.",
        )

        result = await assimilate_usecase_with_vectors.execute(request)
        assert len(result.assimilated_facts) > 1

        # Search for location-specific query
        location_results = await vector_repository.search_semantic_memory(
            entity_id=result.entity.id,
            query_text="What city does this person live in?",
            top_k=5,
        )

        # Top result should be location-related
        assert len(location_results) > 0
        # The top result should contain "London" (the location fact)
        top_fact_id = location_results[0].fact_id.lower()
        assert "london" in top_fact_id or "location" in top_fact_id

    @pytest.mark.asyncio
    async def test_assimilate_stores_correct_vector_metadata(
        self,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        qdrant_client: AsyncQdrantClient,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that vectors include correct metadata (tenant_id, entity_id, fact_id, verb, type)."""
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Berlin.",
        )

        result = await assimilate_usecase_with_vectors.execute(request)
        assert len(result.assimilated_facts) > 0

        # Query Qdrant directly to check payload
        response = await qdrant_client.scroll(
            collection_name=TEST_QDRANT_COLLECTION,
            limit=10,
            with_payload=True,
        )

        # Assert: Points have correct metadata
        points = response[0]
        assert len(points) > 0

        for point in points:
            payload = point.payload
            assert payload is not None
            assert payload.get("tenant_id") == "test_tenant"
            assert payload.get("entity_id") == str(result.entity.id)
            assert payload.get("type") == "semantic"
            assert payload.get("fact_id") is not None
            assert payload.get("verb") is not None
            assert payload.get("relationship_key") is not None


# ----> BACK HERE
class TestAssimilateKnowledgeBackwardCompatibility:
    """Tests for backward compatibility without vector repository."""

    @pytest.mark.asyncio
    async def test_assimilate_works_without_vector_repository(
        self,
        assimilate_usecase_without_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that assimilation works when vector_repository is not provided."""
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Madrid and work as an Architect.",
        )

        # Act - should not raise any errors
        result = await assimilate_usecase_without_vectors.execute(request)

        # Assert: Core functionality still works
        assert result.entity is not None
        assert result.source is not None
        assert len(result.assimilated_facts) > 0

    @pytest.mark.asyncio
    async def test_assimilate_without_vectors_creates_graph_data(
        self,
        assimilate_usecase_without_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that assimilation without vectors still creates graph data correctly."""
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I enjoy swimming and cycling.",
        )

        result = await assimilate_usecase_without_vectors.execute(request)

        # Verify entity exists in graph
        graph_entity = await assimilate_usecase_without_vectors.graph_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert graph_entity is not None
        assert graph_entity["entity"].id == result.entity.id


class TestAssimilateKnowledgeVectorGraphConsistency:
    """Tests for vector-to-graph consistency."""

    @pytest.mark.asyncio
    async def test_multiple_assimilations_accumulate_vectors(
        self,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        vector_repository: QdrantRepository,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that multiple assimilations accumulate vectors for the same entity."""
        # First assimilation
        request1 = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Sydney.",
        )
        result1 = await assimilate_usecase_with_vectors.execute(request1)

        # Second assimilation with same identifier
        request2 = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I work as a Teacher.",
        )
        result2 = await assimilate_usecase_with_vectors.execute(request2)

        # Should reuse the same entity
        assert result1.entity.id == result2.entity.id

        # Search should find vectors from both assimilations
        all_results = await vector_repository.search_semantic_memory(
            entity_id=result1.entity.id,
            query_text="Tell me everything about this person",
            top_k=20,
        )

        # Should have facts from both assimilations
        total_facts = len(result1.assimilated_facts) + len(result2.assimilated_facts)
        assert len(all_results) == total_facts

    @pytest.mark.asyncio
    async def test_vector_search_can_find_facts_by_semantic_meaning(
        self,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        vector_repository: QdrantRepository,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that vector search finds facts by semantic meaning, not just keywords."""
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I work as a Software Developer and I'm located in San Francisco.",
        )

        result = await assimilate_usecase_with_vectors.execute(request)

        # Search with synonymous terms (not exact keywords)
        # "residence" instead of "located", "programmer" instead of "developer"
        location_results = await vector_repository.search_semantic_memory(
            entity_id=result.entity.id,
            query_text="What is their residence? Where do they stay?",
            top_k=5,
        )

        profession_results = await vector_repository.search_semantic_memory(
            entity_id=result.entity.id,
            query_text="What is their occupation? Are they a programmer or engineer?",
            top_k=5,
        )

        # Should find results despite different terminology
        assert len(location_results) > 0
        assert len(profession_results) > 0
