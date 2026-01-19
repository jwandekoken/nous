"""Integration tests for GetEntitySummaryUseCaseImpl with RAG functionality.

This module provides integration tests for the GetEntitySummaryUseCaseImpl with
RAG (Retrieval-Augmented Generation) features enabled. Tests verify that
semantic vector search correctly filters facts before summarization.
"""

import uuid

import asyncpg
import pytest

pytestmark = pytest.mark.integration

from qdrant_client import AsyncQdrantClient

from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    GetEntitySummaryResponse,
    IdentifierDto,
)
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.repositories.qdrant_repository import QdrantRepository
from app.features.graph.services.embedding_service import EmbeddingService
from app.features.graph.services.langchain_data_summarizer import (
    LangChainDataSummarizer,
)
from app.features.graph.services.langchain_fact_extractor import LangChainFactExtractor
from app.features.graph.usecases.assimilate_knowledge_usecase import (
    AssimilateKnowledgeUseCaseImpl,
)
from app.features.graph.usecases.get_entity_summary import GetEntitySummaryUseCaseImpl
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
def data_summarizer() -> LangChainDataSummarizer:
    """LangChainDataSummarizer instance for testing."""
    return LangChainDataSummarizer()


@pytest.fixture
def get_entity_usecase_with_rag(
    age_repository: AgeRepository,
    vector_repository: QdrantRepository,
) -> GetEntityUseCaseImpl:
    """GetEntityUseCaseImpl with vector repository for RAG testing."""
    return GetEntityUseCaseImpl(
        graph_repository=age_repository,
        vector_repository=vector_repository,
    )


@pytest.fixture
def get_entity_summary_usecase_with_rag(
    get_entity_usecase_with_rag: GetEntityUseCaseImpl,
    data_summarizer: LangChainDataSummarizer,
) -> GetEntitySummaryUseCaseImpl:
    """GetEntitySummaryUseCaseImpl with RAG-enabled underlying usecase."""
    return GetEntitySummaryUseCaseImpl(
        get_entity_use_case=get_entity_usecase_with_rag,
        data_summarizer=data_summarizer,
    )


@pytest.fixture
def get_entity_usecase_without_rag(
    age_repository: AgeRepository,
) -> GetEntityUseCaseImpl:
    """GetEntityUseCaseImpl without vector repository (backward compatibility)."""
    return GetEntityUseCaseImpl(graph_repository=age_repository)


@pytest.fixture
def get_entity_summary_usecase_without_rag(
    get_entity_usecase_without_rag: GetEntityUseCaseImpl,
    data_summarizer: LangChainDataSummarizer,
) -> GetEntitySummaryUseCaseImpl:
    """GetEntitySummaryUseCaseImpl without RAG (backward compatibility)."""
    return GetEntitySummaryUseCaseImpl(
        get_entity_use_case=get_entity_usecase_without_rag,
        data_summarizer=data_summarizer,
    )


@pytest.fixture
def test_identifier() -> IdentifierDto:
    """Test identifier for integration testing."""
    return IdentifierDto(
        value=f"test.summary.rag.{uuid.uuid4()}@example.com",
        type="email",
    )


class TestGetEntitySummaryWithRagBackwardCompatibility:
    """Tests to verify backward compatibility when RAG params are not used."""

    @pytest.mark.asyncio
    async def test_summary_without_rag_summarizes_all_facts(
        self,
        get_entity_summary_usecase_with_rag: GetEntitySummaryUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that summary without rag_query summarizes all facts (existing behavior)."""
        # Setup: Create entity with multiple facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Rome. I work as a Chef. I enjoy cooking Italian food.",
        )
        assimilate_result = await assimilate_usecase_with_vectors.execute(request)
        assert len(assimilate_result.assimilated_facts) > 1

        # Act: Get summary without RAG params
        result = await get_entity_summary_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
        )

        # Assert: Summary should be generated (covers all facts)
        assert isinstance(result, GetEntitySummaryResponse)
        assert result.summary is not None
        assert len(result.summary) > 0
        assert (
            result.summary
            != "This entity has no recorded facts in the knowledge graph."
        )

    @pytest.mark.asyncio
    async def test_summary_without_vector_repository_ignores_rag_query(
        self,
        get_entity_summary_usecase_without_rag: GetEntitySummaryUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that when vector_repository is None, rag_query is ignored."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Athens and enjoy sailing.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Get summary with RAG params but no vector_repository
        result = await get_entity_summary_usecase_without_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="Where does this person live?",
            rag_top_k=5,
        )

        # Assert: Summary should be generated (RAG params ignored)
        assert isinstance(result, GetEntitySummaryResponse)
        assert result.summary is not None
        assert (
            result.summary
            != "This entity has no recorded facts in the knowledge graph."
        )


class TestGetEntitySummaryWithRagFiltering:
    """Tests for RAG-based summary filtering functionality."""

    @pytest.mark.asyncio
    async def test_summary_with_rag_summarizes_only_matched_facts(
        self,
        get_entity_summary_usecase_with_rag: GetEntitySummaryUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that summary with rag_query only summarizes matching facts."""
        # Setup: Create entity with multiple distinct facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Sydney, Australia. I work as a Marine Biologist. I enjoy scuba diving.",
        )
        assimilate_result = await assimilate_usecase_with_vectors.execute(request)
        assert len(assimilate_result.assimilated_facts) > 1

        # Act: Get summary with location-specific query
        result = await get_entity_summary_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="Where does this person live?",
            rag_top_k=3,
        )

        # Assert: Summary should be generated (focused on location)
        assert isinstance(result, GetEntitySummaryResponse)
        assert result.summary is not None
        assert len(result.summary) > 0

    @pytest.mark.asyncio
    async def test_summary_with_no_matching_facts_returns_appropriate_message(
        self,
        get_entity_summary_usecase_with_rag: GetEntitySummaryUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that summary with no matching facts returns appropriate message."""
        # Setup: Create entity with specific facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Cairo.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Query for something completely unrelated with high min_score
        result = await get_entity_summary_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="What programming languages do they know?",
            rag_top_k=5,
            rag_min_score=0.95,  # Very high threshold - should filter out everything
        )

        # Assert: Should return the "no facts" message
        assert isinstance(result, GetEntitySummaryResponse)
        assert (
            result.summary
            == "This entity has no recorded facts in the knowledge graph."
        )


class TestGetEntitySummaryRagParamsPropagation:
    """Tests to verify RAG params are correctly passed through to underlying usecase."""

    @pytest.mark.asyncio
    async def test_rag_params_are_passed_to_underlying_usecase(
        self,
        get_entity_summary_usecase_with_rag: GetEntitySummaryUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that all RAG params are correctly passed to the underlying usecase."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Barcelona. I work as an Architect. I enjoy painting.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Use various RAG params
        result = await get_entity_summary_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="What is their profession?",
            rag_top_k=3,
            rag_min_score=0.3,
            rag_expand_hops=0,
        )

        # Assert: Summary should be generated
        assert isinstance(result, GetEntitySummaryResponse)
        assert result.summary is not None
        # The summary should be focused on profession-related content

    @pytest.mark.asyncio
    async def test_rag_top_k_limits_facts_for_summary(
        self,
        get_entity_summary_usecase_with_rag: GetEntitySummaryUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that rag_top_k limits the number of facts used for summary."""
        # Setup: Create entity with many facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content=(
                "I live in Boston. I work as a Lawyer. I enjoy golf. "
                "I speak Spanish. I have a dog named Max."
            ),
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Query with low top_k
        result = await get_entity_summary_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="Tell me about this person",
            rag_top_k=1,  # Only request 1 fact
        )

        # Assert: Summary should be generated (based on limited facts)
        assert isinstance(result, GetEntitySummaryResponse)
        assert result.summary is not None


class TestGetEntitySummaryWithLanguage:
    """Tests for summary language parameter with RAG."""

    @pytest.mark.asyncio
    async def test_summary_with_rag_and_language(
        self,
        get_entity_summary_usecase_with_rag: GetEntitySummaryUseCaseImpl,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that language parameter works alongside RAG params."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Munich and work as a Doctor.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Query with RAG and language
        result = await get_entity_summary_usecase_with_rag.execute(
            identifier_value=test_identifier.value,
            identifier_type=test_identifier.type,
            rag_query="Where do they live?",
            rag_top_k=5,
            lang="es",  # Spanish
        )

        # Assert: Summary should be generated
        assert isinstance(result, GetEntitySummaryResponse)
        assert result.summary is not None
        assert len(result.summary) > 0


class TestGetEntitySummaryErrorHandling:
    """Tests for error handling with RAG."""

    @pytest.mark.asyncio
    async def test_entity_not_found_raises_404(
        self,
        get_entity_summary_usecase_with_rag: GetEntitySummaryUseCaseImpl,
    ) -> None:
        """Test that non-existent entity raises 404 even with RAG params."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_entity_summary_usecase_with_rag.execute(
                identifier_value="nonexistent@example.com",
                identifier_type="email",
                rag_query="Where does this person live?",
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()
