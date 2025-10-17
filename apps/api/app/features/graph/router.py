"""Graph database API routes - main router that includes all entity-specific route modules."""

from typing import Protocol

from fastapi import APIRouter, Depends

from app.db.postgres.connection import get_db_pool
from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    AssimilateKnowledgeResponse,
    GetEntityResponse,
)
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.services.langchain_fact_extractor import LangChainFactExtractor
from app.features.graph.usecases import (
    AssimilateKnowledgeUseCaseImpl,
    GetEntityUseCaseImpl,
)


class AssimilateKnowledgeUseCase(Protocol):
    """Protocol for the assimilate knowledge use case."""

    async def execute(
        self, request: AssimilateKnowledgeRequest
    ) -> AssimilateKnowledgeResponse:
        """Process content and associate facts with an entity."""
        ...


class GetEntityUseCase(Protocol):
    """Protocol for the get entity use case."""

    async def execute(
        self, identifier_value: str, identifier_type: str
    ) -> GetEntityResponse:
        """Retrieve entity information by identifier."""
        ...


router = APIRouter(prefix="/graph", tags=["graph"])


# Create the fact extractor instance at module level to avoid instantiation issues
_fact_extractor = LangChainFactExtractor()


async def get_assimilate_knowledge_use_case() -> AssimilateKnowledgeUseCase:
    """Dependency injection for the assimilate knowledge use case."""

    pool = await get_db_pool()
    return AssimilateKnowledgeUseCaseImpl(
        repository=AgeRepository(pool), fact_extractor=_fact_extractor
    )


async def get_get_entity_use_case() -> GetEntityUseCase:
    """Dependency injection for the get entity use case."""

    pool = await get_db_pool()
    return GetEntityUseCaseImpl(repository=AgeRepository(pool))


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


@router.get("/entities/lookup", response_model=GetEntityResponse)
async def get_entity(
    type: str,
    value: str,
    use_case: GetEntityUseCase = Depends(get_get_entity_use_case),
) -> GetEntityResponse:
    """Retrieve entity information by identifier.

    This endpoint looks up an entity using an external identifier (e.g., email, phone)
    and returns the entity details along with all associated facts and their sources.
    """

    return await use_case.execute(identifier_value=value, identifier_type=type)
