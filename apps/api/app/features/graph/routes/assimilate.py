"""Assimilate knowledge route handler."""

import logging
from typing import Protocol

from fastapi import APIRouter, Depends

from app.core.authorization import TenantInfo, get_tenant_info
from app.core.settings import get_settings
from app.db.postgres.graph_connection import get_graph_db_pool
from app.db.qdrant import get_qdrant_client
from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    AssimilateKnowledgeResponse,
)
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.repositories.vector_repository import VectorRepository
from app.features.graph.services.embedding_service import EmbeddingService
from app.features.graph.services.langchain_fact_extractor import LangChainFactExtractor
from app.features.graph.usecases import AssimilateKnowledgeUseCaseImpl

logger = logging.getLogger(__name__)


class AssimilateKnowledgeUseCase(Protocol):
    """Protocol for the assimilate knowledge use case."""

    async def execute(
        self, request: AssimilateKnowledgeRequest
    ) -> AssimilateKnowledgeResponse:
        """Process content and associate facts with an entity."""
        ...


# Create the fact extractor instance at module level to avoid instantiation issues
_fact_extractor = LangChainFactExtractor()

# Create the embedding service at module level (lazy initialization)
_embedding_service: EmbeddingService | None = None


def _get_embedding_service() -> EmbeddingService | None:
    """Get or create the embedding service singleton.

    Returns None if the service cannot be initialized (e.g., missing API key).
    This allows graceful degradation without breaking the assimilate endpoint.
    """
    global _embedding_service
    if _embedding_service is None:
        try:
            _embedding_service = EmbeddingService()
        except ValueError as e:
            logger.warning("EmbeddingService initialization failed: %s", e)
            return None
    return _embedding_service


async def get_assimilate_knowledge_use_case(
    tenant_info: TenantInfo = Depends(get_tenant_info),
) -> AssimilateKnowledgeUseCase:
    """Dependency injection for the assimilate knowledge use case."""
    settings = get_settings()
    pool = await get_graph_db_pool()
    repository = AgeRepository(pool, graph_name=tenant_info.graph_name)

    # Create vector repository if embedding service is available
    vector_repository: VectorRepository | None = None
    embedding_service = _get_embedding_service()
    if embedding_service:
        qdrant_client = await get_qdrant_client()
        vector_repository = VectorRepository(
            client=qdrant_client,
            embedding_service=embedding_service,
            tenant_id=str(tenant_info.tenant_id),
            collection_name=settings.vector_collection_name,
        )

    return AssimilateKnowledgeUseCaseImpl(
        repository=repository,
        fact_extractor=_fact_extractor,
        vector_repository=vector_repository,
    )


router = APIRouter()


@router.post("/entities/assimilate", response_model=AssimilateKnowledgeResponse)
async def assimilate_knowledge(
    request: AssimilateKnowledgeRequest,
    use_case: AssimilateKnowledgeUseCase = Depends(get_assimilate_knowledge_use_case),
) -> AssimilateKnowledgeResponse:
    """Assimilate knowledge by processing content and associating facts with an entity.

    This endpoint processes textual content, extracts facts, and associates them
    with the specified entity in the knowledge graph.
    """

    return await use_case.execute(request)
