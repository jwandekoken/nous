"""Assimilate knowledge route handler."""

from typing import Protocol

from fastapi import APIRouter, Depends

from app.core.authorization import TenantInfo, get_tenant_info
from app.db.postgres.graph_connection import get_graph_db_pool
from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    AssimilateKnowledgeResponse,
)
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.services.langchain_fact_extractor import LangChainFactExtractor
from app.features.graph.usecases import AssimilateKnowledgeUseCaseImpl


class AssimilateKnowledgeUseCase(Protocol):
    """Protocol for the assimilate knowledge use case."""

    async def execute(
        self, request: AssimilateKnowledgeRequest
    ) -> AssimilateKnowledgeResponse:
        """Process content and associate facts with an entity."""
        ...


# Create the fact extractor instance at module level to avoid instantiation issues
_fact_extractor = LangChainFactExtractor()


async def get_assimilate_knowledge_use_case(
    tenant_info: TenantInfo = Depends(get_tenant_info),
) -> AssimilateKnowledgeUseCase:
    """Dependency injection for the assimilate knowledge use case."""

    pool = await get_graph_db_pool()
    repository = AgeRepository(pool, graph_name=tenant_info.graph_name)
    return AssimilateKnowledgeUseCaseImpl(
        repository=repository, fact_extractor=_fact_extractor
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
