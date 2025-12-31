"""Entity lookup route handler."""

import logging
from typing import Protocol

from fastapi import APIRouter, Depends

from app.core.authorization import TenantInfo, get_tenant_info
from app.core.settings import get_settings
from app.db.postgres.graph_connection import get_graph_db_pool
from app.db.qdrant import get_qdrant_client
from app.features.graph.dtos.knowledge_dto import (
    GetEntityResponse,
    GetEntitySummaryResponse,
)
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.repositories.protocols import VectorRepository
from app.features.graph.repositories.qdrant_repository import QdrantRepository
from app.features.graph.services.embedding_service import EmbeddingService
from app.features.graph.services.langchain_data_summarizer import (
    LangChainDataSummarizer,
)
from app.features.graph.usecases import GetEntityUseCaseImpl
from app.features.graph.usecases.get_entity_summary import (
    GetEntitySummaryUseCaseImpl,
)

logger = logging.getLogger(__name__)


class GetEntityUseCase(Protocol):
    """Protocol for the get entity use case."""

    async def execute(
        self,
        identifier_value: str,
        identifier_type: str,
        rag_query: str | None = None,
        rag_top_k: int = 10,
        rag_min_score: float | None = None,
        rag_expand_hops: int = 0,
        rag_debug: bool = False,
    ) -> GetEntityResponse:
        """Retrieve entity information by identifier."""
        ...


class GetEntitySummaryUseCase(Protocol):
    """Protocol for the get entity summary use case."""

    async def execute(
        self,
        identifier_value: str,
        identifier_type: str,
        lang: str | None = None,
        rag_query: str | None = None,
        rag_top_k: int = 10,
        rag_min_score: float | None = None,
        rag_expand_hops: int = 0,
    ) -> GetEntitySummaryResponse:
        """Generate a natural language summary of entity data."""
        ...


# Create the data summarizer instance at module level
_data_summarizer = LangChainDataSummarizer()

# Create the embedding service at module level (lazy initialization)
_embedding_service: EmbeddingService | None = None


def _get_embedding_service() -> EmbeddingService | None:
    """Get or create the embedding service singleton.

    Returns None if the service cannot be initialized (e.g., missing API key).
    This allows graceful degradation - lookups will work but without RAG filtering.
    """
    global _embedding_service
    if _embedding_service is None:
        try:
            _embedding_service = EmbeddingService()
        except ValueError as e:
            logger.warning("EmbeddingService initialization failed: %s", e)
            return None
    return _embedding_service


async def _get_vector_repository(tenant_info: TenantInfo) -> VectorRepository | None:
    """Get a VectorRepository instance for the tenant.

    Returns None if the embedding service is unavailable.
    """
    embedding_service = _get_embedding_service()
    if embedding_service is None:
        return None

    settings = get_settings()
    qdrant_client = await get_qdrant_client()
    return QdrantRepository(
        client=qdrant_client,
        embedding_service=embedding_service,
        tenant_id=str(tenant_info.tenant_id),
        collection_name=settings.vector_collection_name,
    )


async def get_get_entity_use_case(
    tenant_info: TenantInfo = Depends(get_tenant_info),
) -> GetEntityUseCase:
    """Dependency injection for the get entity use case."""
    pool = await get_graph_db_pool()
    repository = AgeRepository(pool, graph_name=tenant_info.graph_name)
    vector_repository = await _get_vector_repository(tenant_info)

    return GetEntityUseCaseImpl(
        repository=repository,
        vector_repository=vector_repository,
    )


async def get_entity_summary_use_case(
    tenant_info: TenantInfo = Depends(get_tenant_info),
) -> GetEntitySummaryUseCase:
    """Dependency injection for the entity summary use case."""
    pool = await get_graph_db_pool()
    repository = AgeRepository(pool, graph_name=tenant_info.graph_name)
    vector_repository = await _get_vector_repository(tenant_info)

    get_entity_use_case = GetEntityUseCaseImpl(
        repository=repository,
        vector_repository=vector_repository,
    )
    return GetEntitySummaryUseCaseImpl(
        get_entity_use_case=get_entity_use_case, data_summarizer=_data_summarizer
    )


router = APIRouter()


@router.get("/entities/lookup", response_model=GetEntityResponse)
async def get_entity(
    type: str,
    value: str,
    rag_query: str | None = None,
    rag_top_k: int = 10,
    rag_min_score: float | None = None,
    rag_expand_hops: int = 0,
    rag_debug: bool = False,
    use_case: GetEntityUseCase = Depends(get_get_entity_use_case),
) -> GetEntityResponse:
    """Retrieve entity information by identifier.

    This endpoint looks up an entity using an external identifier (e.g., email, phone)
    and returns the entity details along with all associated facts and their sources.

    Args:
        type: The identifier type (e.g., 'email', 'phone')
        value: The identifier value (e.g., 'user@example.com')
        rag_query: Optional conversational query for semantic search
        rag_top_k: Number of vector candidates to retrieve (default: 10)
        rag_min_score: Optional similarity threshold for filtering vector hits
        rag_expand_hops: Optional graph expansion depth (default: 0)
        rag_debug: Whether to return debug metadata (default: False)
    """

    return await use_case.execute(
        identifier_value=value,
        identifier_type=type,
        rag_query=rag_query,
        rag_top_k=rag_top_k,
        rag_min_score=rag_min_score,
        rag_expand_hops=rag_expand_hops,
        rag_debug=rag_debug,
    )


@router.get("/entities/lookup/summary", response_model=GetEntitySummaryResponse)
async def get_entity_summary(
    type: str,
    value: str,
    lang: str | None = None,
    rag_query: str | None = None,
    rag_top_k: int = 10,
    rag_min_score: float | None = None,
    rag_expand_hops: int = 0,
    use_case: GetEntitySummaryUseCase = Depends(get_entity_summary_use_case),
) -> GetEntitySummaryResponse:
    """Generate a natural language summary of entity data.

    This endpoint looks up an entity using an external identifier (e.g., email, phone)
    and returns a concise textual summary of all known facts and relationships.
    The summary is optimized for consumption by Large Language Models.

    Args:
        type: The identifier type (e.g., 'email', 'phone')
        value: The identifier value (e.g., 'user@example.com')
        lang: Optional language code for the summary (e.g., 'pt-br', 'es', 'fr'). Defaults to English.
        rag_query: Optional conversational query for semantic search
        rag_top_k: Number of vector candidates to retrieve (default: 10)
        rag_min_score: Optional similarity threshold for filtering vector hits
        rag_expand_hops: Optional graph expansion depth (default: 0)
    """
    return await use_case.execute(
        identifier_value=value,
        identifier_type=type,
        lang=lang,
        rag_query=rag_query,
        rag_top_k=rag_top_k,
        rag_min_score=rag_min_score,
        rag_expand_hops=rag_expand_hops,
    )
