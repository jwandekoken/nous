"""Integration tests for lookup routes with RAG functionality.

This module provides integration tests for the lookup route handlers with
RAG (Retrieval-Augmented Generation) features enabled. Tests verify the
full HTTP request/response cycle including proper response shapes.
"""

import uuid
from collections.abc import AsyncGenerator

import asyncpg
import pytest

pytestmark = pytest.mark.integration

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from qdrant_client import AsyncQdrantClient

from app.core.authorization import TenantInfo
from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    IdentifierDto,
)
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.repositories.qdrant_repository import QdrantRepository
from app.features.graph.routes.lookup import router
from app.features.graph.services.embedding_service import EmbeddingService
from app.features.graph.services.langchain_data_summarizer import (
    LangChainDataSummarizer,
)
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
def test_identifier() -> IdentifierDto:
    """Test identifier for integration testing."""
    return IdentifierDto(
        value=f"test.route.rag.{uuid.uuid4()}@example.com",
        type="email",
    )


@pytest.fixture
def tenant_info() -> TenantInfo:
    """Mock tenant info for testing."""
    return TenantInfo(
        tenant_id=uuid.uuid4(),
        graph_name="test_graph",
    )


@pytest.fixture
def app(
    age_repository: AgeRepository,
    vector_repository: QdrantRepository,
    tenant_info: TenantInfo,
) -> FastAPI:
    """Create a test FastAPI app with the lookup router."""
    from app.core.authorization import get_tenant_info
    from app.features.graph.routes.lookup import (
        get_entity_summary_use_case,
        get_get_entity_use_case,
    )
    from app.features.graph.usecases.get_entity_summary import (
        GetEntitySummaryUseCaseImpl,
    )
    from app.features.graph.usecases.get_entity_usecase import GetEntityUseCaseImpl

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/graph")

    # Override tenant dependency
    async def mock_get_tenant_info() -> TenantInfo:
        return tenant_info

    # Override use case dependencies to use our test repositories
    async def mock_get_entity_use_case() -> GetEntityUseCaseImpl:
        return GetEntityUseCaseImpl(
            graph_repository=age_repository,
            vector_repository=vector_repository,
        )

    async def mock_get_entity_summary_use_case() -> GetEntitySummaryUseCaseImpl:
        get_entity_use_case = GetEntityUseCaseImpl(
            graph_repository=age_repository,
            vector_repository=vector_repository,
        )
        return GetEntitySummaryUseCaseImpl(
            get_entity_use_case=get_entity_use_case,
            data_summarizer=LangChainDataSummarizer(),
        )

    app.dependency_overrides[get_tenant_info] = mock_get_tenant_info
    app.dependency_overrides[get_get_entity_use_case] = mock_get_entity_use_case
    app.dependency_overrides[get_entity_summary_use_case] = (
        mock_get_entity_summary_use_case
    )

    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestLookupEndpointWithRag:
    """Tests for /entities/lookup endpoint with RAG params."""

    @pytest.mark.asyncio
    async def test_lookup_without_rag_params(
        self,
        client: AsyncClient,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that lookup works without RAG params (backward compatibility)."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Warsaw and work as a Dentist.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Call endpoint without RAG params
        response = await client.get(
            "/api/v1/graph/entities/lookup",
            params={
                "type": test_identifier.type,
                "value": test_identifier.value,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "entity" in data
        assert "identifier" in data
        assert "facts" in data
        assert len(data["facts"]) > 0

    @pytest.mark.asyncio
    async def test_lookup_with_rag_query(
        self,
        client: AsyncClient,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that lookup works with rag_query parameter."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Stockholm. I work as a Pilot. I enjoy skiing.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Call endpoint with RAG params
        response = await client.get(
            "/api/v1/graph/entities/lookup",
            params={
                "type": test_identifier.type,
                "value": test_identifier.value,
                "rag_query": "Where does this person live?",
                "rag_top_k": 3,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "entity" in data
        assert "facts" in data
        # Should have fewer facts due to RAG filtering
        assert len(data["facts"]) > 0

    @pytest.mark.asyncio
    async def test_lookup_with_rag_debug(
        self,
        client: AsyncClient,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that lookup returns debug metadata when rag_debug=true."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Copenhagen.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Call endpoint with debug enabled
        response = await client.get(
            "/api/v1/graph/entities/lookup",
            params={
                "type": test_identifier.type,
                "value": test_identifier.value,
                "rag_query": "What city?",
                "rag_debug": "true",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "rag_debug" in data
        assert data["rag_debug"] is not None
        assert "query" in data["rag_debug"]
        assert "vector_hits" in data["rag_debug"]
        assert "verified_count" in data["rag_debug"]

    @pytest.mark.asyncio
    async def test_lookup_with_min_score(
        self,
        client: AsyncClient,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that lookup respects rag_min_score parameter."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Oslo.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Call endpoint with high min_score
        response = await client.get(
            "/api/v1/graph/entities/lookup",
            params={
                "type": test_identifier.type,
                "value": test_identifier.value,
                "rag_query": "programming languages",
                "rag_min_score": 0.95,
            },
        )

        # Assert: Should return empty facts due to high threshold
        assert response.status_code == 200
        data = response.json()
        assert "facts" in data
        # High min_score with unrelated query should filter out all facts
        assert len(data["facts"]) == 0

    @pytest.mark.asyncio
    async def test_lookup_entity_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that lookup returns 404 for non-existent entity."""
        response = await client.get(
            "/api/v1/graph/entities/lookup",
            params={
                "type": "email",
                "value": "nonexistent@example.com",
                "rag_query": "something",
            },
        )

        assert response.status_code == 404


class TestLookupSummaryEndpointWithRag:
    """Tests for /entities/lookup/summary endpoint with RAG params."""

    @pytest.mark.asyncio
    async def test_summary_without_rag_params(
        self,
        client: AsyncClient,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that summary works without RAG params (backward compatibility)."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Helsinki and work as a Nurse.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Call endpoint without RAG params
        response = await client.get(
            "/api/v1/graph/entities/lookup/summary",
            params={
                "type": test_identifier.type,
                "value": test_identifier.value,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert len(data["summary"]) > 0
        assert (
            data["summary"]
            != "This entity has no recorded facts in the knowledge graph."
        )

    @pytest.mark.asyncio
    async def test_summary_with_rag_query(
        self,
        client: AsyncClient,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that summary works with rag_query parameter."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Brussels. I work as a Banker. I enjoy tennis.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Call endpoint with RAG params
        response = await client.get(
            "/api/v1/graph/entities/lookup/summary",
            params={
                "type": test_identifier.type,
                "value": test_identifier.value,
                "rag_query": "What is their profession?",
                "rag_top_k": 3,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert len(data["summary"]) > 0

    @pytest.mark.asyncio
    async def test_summary_with_language_and_rag(
        self,
        client: AsyncClient,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that summary works with both language and RAG params."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Geneva.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Call endpoint with language and RAG params
        response = await client.get(
            "/api/v1/graph/entities/lookup/summary",
            params={
                "type": test_identifier.type,
                "value": test_identifier.value,
                "lang": "fr",
                "rag_query": "Où habite cette personne?",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert len(data["summary"]) > 0

    @pytest.mark.asyncio
    async def test_summary_with_no_matching_facts(
        self,
        client: AsyncClient,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that summary returns appropriate message when no facts match."""
        # Setup: Create entity with facts
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Zurich.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act: Call endpoint with unrelated query and high min_score
        response = await client.get(
            "/api/v1/graph/entities/lookup/summary",
            params={
                "type": test_identifier.type,
                "value": test_identifier.value,
                "rag_query": "programming skills",
                "rag_min_score": 0.95,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert (
            data["summary"]
            == "This entity has no recorded facts in the knowledge graph."
        )

    @pytest.mark.asyncio
    async def test_summary_entity_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that summary returns 404 for non-existent entity."""
        response = await client.get(
            "/api/v1/graph/entities/lookup/summary",
            params={
                "type": "email",
                "value": "nonexistent@example.com",
                "rag_query": "something",
            },
        )

        assert response.status_code == 404


class TestLookupEndpointResponseShape:
    """Tests to verify correct response shapes for lookup endpoints."""

    @pytest.mark.asyncio
    async def test_lookup_response_contains_all_required_fields(
        self,
        client: AsyncClient,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that lookup response contains all required fields."""
        # Setup
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Dublin.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act
        response = await client.get(
            "/api/v1/graph/entities/lookup",
            params={
                "type": test_identifier.type,
                "value": test_identifier.value,
                "rag_query": "location",
                "rag_debug": "true",
            },
        )

        # Assert response structure
        assert response.status_code == 200
        data = response.json()

        # Entity
        assert "entity" in data
        assert "id" in data["entity"]
        assert "created_at" in data["entity"]
        assert "metadata" in data["entity"]

        # Identifier
        assert "identifier" in data
        assert "identifier" in data["identifier"]
        assert "relationship" in data["identifier"]
        assert data["identifier"]["identifier"]["value"] == test_identifier.value
        assert data["identifier"]["identifier"]["type"] == test_identifier.type

        # Facts
        assert "facts" in data
        if len(data["facts"]) > 0:
            fact = data["facts"][0]
            assert "fact" in fact
            assert "name" in fact["fact"]
            assert "type" in fact["fact"]
            assert "fact_id" in fact["fact"]
            assert "relationship" in fact
            assert "verb" in fact["relationship"]

        # RAG debug (when enabled)
        assert "rag_debug" in data
        if data["rag_debug"] is not None:
            debug = data["rag_debug"]
            assert "query" in debug
            assert "top_k" in debug
            assert "vector_hits" in debug
            assert "verified_count" in debug
            assert "timings_ms" in debug

    @pytest.mark.asyncio
    async def test_summary_response_contains_summary_field(
        self,
        client: AsyncClient,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that summary response contains the summary field."""
        # Setup
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="I live in Edinburgh.",
        )
        await assimilate_usecase_with_vectors.execute(request)

        # Act
        response = await client.get(
            "/api/v1/graph/entities/lookup/summary",
            params={
                "type": test_identifier.type,
                "value": test_identifier.value,
                "rag_query": "location",
            },
        )

        # Assert response structure
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert isinstance(data["summary"], str)
        assert len(data["summary"]) > 0
