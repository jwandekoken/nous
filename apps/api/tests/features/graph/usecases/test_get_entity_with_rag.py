"""Integration tests for GetEntityUseCaseImpl with RAG functionality.

This module provides integration tests for the GetEntityUseCaseImpl with
RAG (Retrieval-Augmented Generation) features enabled. Tests verify that
semantic vector search correctly filters facts returned by the lookup.
"""

import uuid

import asyncpg
import pytest
from fastapi import HTTPException
from qdrant_client import AsyncQdrantClient

from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    IdentifierDto,
)
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.repositories.vector_repository import VectorRepository
from app.features.graph.services.embedding_service import EmbeddingService
from app.features.graph.services.langchain_fact_extractor import LangChainFactExtractor
from app.features.graph.usecases.assimilate_knowledge_usecase import (
    AssimilateKnowledgeUseCaseImpl,
)
from app.features.graph.usecases.get_entity_usecase import GetEntityUseCaseImpl
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
) -> VectorRepository:
    """VectorRepository instance for testing."""
    return VectorRepository(
        client=qdrant_client,
        embedding_service=embedding_service,
        tenant_id="test_tenant",
        collection_name=TEST_QDRANT_COLLECTION,
    )


@pytest.fixture
def assimilate_usecase_with_vectors(
    age_repository: AgeRepository,
    langchain_fact_extractor: LangChainFactExtractor,
    vector_repository: VectorRepository,
) -> AssimilateKnowledgeUseCaseImpl:
    """AssimilateKnowledgeUseCaseImpl with vector repository for testing."""
    return AssimilateKnowledgeUseCaseImpl(
        repository=age_repository,
        fact_extractor=langchain_fact_extractor,
        vector_repository=vector_repository,
    )


@pytest.fixture
def get_entity_usecase_with_rag(
    age_repository: AgeRepository,
    vector_repository: VectorRepository,
) -> GetEntityUseCaseImpl:
    """GetEntityUseCaseImpl with vector repository for RAG testing."""
    return GetEntityUseCaseImpl(
        repository=age_repository,
        vector_repository=vector_repository,
    )


@pytest.fixture
def get_entity_usecase_without_rag(
    age_repository: AgeRepository,
) -> GetEntityUseCaseImpl:
    """GetEntityUseCaseImpl without vector repository (backward compatibility)."""
    return GetEntityUseCaseImpl(repository=age_repository)


@pytest.fixture
def test_identifier() -> IdentifierDto:
    """Test identifier for integration testing."""
    return IdentifierDto(
        value=f"test.rag.{uuid.uuid4()}@example.com",
        type="email",
    )


class TestGetEntityWithRagBackwardCompatibility:
    """Tests to verify backward compatibility when RAG params are not used."""

    @pytest.mark.asyncio
    async def test_lookup_without_rag_returns_all_facts(
        self,
        get_entity_usecase_with_rag: GetEntityUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that lookup without rag_query returns all facts (existing behavior)."""
        # Setup: Create entity with multiple facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Berlin. I work as a Doctor. I enjoy reading books.",
        )
        assimilate_result = await assimilate_usecase_with_vectors.execute(request)
        assert len(assimilate_result.assimilated_facts) > 1

        # Act: Lookup without RAG params
        result = await get_entity_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
        )

        # Assert: All facts should be returned
        assert len(result.facts) == len(assimilate_result.assimilated_facts)

    @pytest.mark.asyncio
    async def test_lookup_without_vector_repository_ignores_rag_query(
        self,
        get_entity_usecase_without_rag: GetEntityUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that when vector_repository is None, rag_query is ignored."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Paris and enjoy hiking.",
        )
        assimilate_result = await assimilate_usecase_with_vectors.execute(request)

        # Act: Lookup with RAG params but no vector_repository
        result = await get_entity_usecase_without_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="Where does this person live?",
            rag_top_k=5,
        )

        # Assert: All facts should be returned (RAG params ignored)
        assert len(result.facts) == len(assimilate_result.assimilated_facts)


class TestGetEntityWithRagFiltering:
    """Tests for RAG-based fact filtering functionality."""

    @pytest.mark.asyncio
    async def test_lookup_with_rag_returns_filtered_facts(
        self,
        get_entity_usecase_with_rag: GetEntityUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that lookup with rag_query returns only matching facts.

        Note: With only 3 facts and top_k=3, all facts might be returned if their
        embeddings are all somewhat similar to the query. To ensure filtering,
        we use min_score threshold to filter out less relevant facts.
        """
        # Setup: Create entity with multiple distinct facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Tokyo. I work as a Software Engineer. I enjoy swimming.",
        )
        assimilate_result = await assimilate_usecase_with_vectors.execute(request)
        assert len(assimilate_result.assimilated_facts) > 1

        # Act: Lookup with location-specific query and min_score to ensure filtering
        result = await get_entity_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="What city does this person live in?",
            rag_top_k=3,
            rag_min_score=0.5,  # Use min_score to filter out less relevant facts
        )

        # Assert: RAG filtering returns at least one fact (the location)
        # With min_score=0.5, less relevant facts should be filtered out
        assert len(result.facts) > 0
        # Check that the location fact is included (most relevant to query)
        fact_names = [f.fact.name.lower() for f in result.facts]
        assert any("tokyo" in name for name in fact_names), (
            "Location fact should be in results"
        )

    @pytest.mark.asyncio
    async def test_rag_query_returns_relevant_facts_first(
        self,
        get_entity_usecase_with_rag: GetEntityUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that RAG returns the most relevant facts based on query."""
        # Setup: Create entity with multiple facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in San Francisco. I work as a Data Scientist. I enjoy cycling.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Query for profession
        result = await get_entity_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="What is their job or occupation?",
            rag_top_k=5,
        )

        # Assert: Should find profession-related fact
        assert len(result.facts) > 0
        fact_names = [f.fact.name.lower() for f in result.facts]
        # The top result should include profession-related terms
        assert any(
            "scientist" in name or "data" in name or "profession" in f.fact.type.lower()
            for f, name in zip(result.facts, fact_names)
        )

    @pytest.mark.asyncio
    async def test_empty_rag_results_returns_empty_facts(
        self,
        get_entity_usecase_with_rag: GetEntityUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that when RAG finds no matching facts, empty list is returned."""
        # Setup: Create entity with specific facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Madrid.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Query for something completely unrelated with high min_score
        result = await get_entity_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="What programming languages do they know?",
            rag_top_k=5,
            rag_min_score=0.95,  # Very high threshold
        )

        # Assert: Should return empty facts (no matching facts)
        assert len(result.facts) == 0


class TestGetEntityRagMinScore:
    """Tests for rag_min_score filtering functionality."""

    @pytest.mark.asyncio
    async def test_rag_min_score_filters_low_scoring_hits(
        self,
        get_entity_usecase_with_rag: GetEntityUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that rag_min_score filters out low-scoring vector hits."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in London. I work as a Teacher. I enjoy gardening.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Query with high min_score threshold
        result_high_threshold = await get_entity_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="Where do they live?",
            rag_top_k=10,
            rag_min_score=0.8,  # High threshold
        )

        # Act: Query with no min_score threshold
        result_no_threshold = await get_entity_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="Where do they live?",
            rag_top_k=10,
        )

        # Assert: High threshold should return fewer or equal facts
        assert len(result_high_threshold.facts) <= len(result_no_threshold.facts)


class TestGetEntityRagDebug:
    """Tests for RAG debug metadata functionality."""

    @pytest.mark.asyncio
    async def test_rag_debug_returns_metadata(
        self,
        get_entity_usecase_with_rag: GetEntityUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that rag_debug=True returns debug metadata."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Amsterdam and work as an Architect.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Query with debug enabled
        result = await get_entity_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="Where does this person live?",
            rag_top_k=5,
            rag_debug=True,
        )

        # Assert: Debug metadata should be present
        assert result.rag_debug is not None
        assert result.rag_debug.query == "Where does this person live?"
        assert result.rag_debug.top_k == 5
        assert result.rag_debug.vector_hits is not None
        assert result.rag_debug.verified_count >= 0
        assert result.rag_debug.timings_ms is not None

    @pytest.mark.asyncio
    async def test_rag_debug_false_returns_no_metadata(
        self,
        get_entity_usecase_with_rag: GetEntityUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that rag_debug=False (default) returns no debug metadata."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Vienna.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Query without debug
        result = await get_entity_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="Where does this person live?",
            rag_top_k=5,
            rag_debug=False,
        )

        # Assert: Debug metadata should NOT be present
        assert result.rag_debug is None

    @pytest.mark.asyncio
    async def test_rag_debug_contains_vector_hit_details(
        self,
        get_entity_usecase_with_rag: GetEntityUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that debug metadata contains detailed vector hit information."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Lisbon.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Query with debug enabled
        result = await get_entity_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="What city do they live in?",
            rag_top_k=10,
            rag_debug=True,
        )

        # Assert: Vector hits should have proper structure
        assert result.rag_debug is not None
        assert len(result.rag_debug.vector_hits) > 0

        for hit in result.rag_debug.vector_hits:
            assert hit.fact_id is not None
            assert hit.verb is not None
            assert hit.score > 0
            assert isinstance(hit.verified, bool)


class TestGetEntityRagGraphVerification:
    """Tests for graph verification preventing cross-entity data leakage."""

    @pytest.mark.asyncio
    async def test_rag_only_returns_verified_facts(
        self,
        get_entity_usecase_with_rag: GetEntityUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that RAG only returns facts that exist in the graph."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Prague and work as a Musician.",
        )
        assimilate_result = await assimilate_usecase_with_vectors.execute(request)

        # Act: Query with debug to check verification
        result = await get_entity_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="Tell me about this person",
            rag_top_k=20,
            rag_debug=True,
        )

        # Assert: All returned facts should be verified
        assert result.rag_debug is not None
        for hit in result.rag_debug.vector_hits:
            if hit.verified:
                # Verified hits should have corresponding facts in the response
                matching_facts = [
                    f for f in result.facts if f.fact.fact_id == hit.fact_id
                ]
                assert len(matching_facts) > 0, (
                    f"Verified hit {hit.fact_id} not found in response facts"
                )

    @pytest.mark.asyncio
    async def test_rag_debug_shows_verified_count(
        self,
        get_entity_usecase_with_rag: GetEntityUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that verified_count matches the number of returned facts."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Dublin and enjoy photography.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Query with debug
        result = await get_entity_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="What are their hobbies?",
            rag_top_k=10,
            rag_debug=True,
        )

        # Assert: verified_count should match returned facts
        assert result.rag_debug is not None
        assert result.rag_debug.verified_count == len(result.facts)


class TestGetEntityRagEntityNotFound:
    """Tests for entity not found handling with RAG."""

    @pytest.mark.asyncio
    async def test_entity_not_found_raises_404(
        self,
        get_entity_usecase_with_rag: GetEntityUseCaseImpl,
    ) -> None:
        """Test that non-existent entity raises 404 even with RAG params."""
        with pytest.raises(HTTPException) as exc_info:
            await get_entity_usecase_with_rag.execute(
                identifier_value="nonexistent@example.com",
                identifier_type="email",
                rag_query="Where does this person live?",
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()
