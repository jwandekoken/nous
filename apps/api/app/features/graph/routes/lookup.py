"""Entity lookup route handler."""

from typing import Protocol

from fastapi import APIRouter, Depends

from app.core.authorization import TenantInfo, get_tenant_info
from app.db.postgres.graph_connection import get_graph_db_pool
from app.features.graph.dtos.knowledge_dto import GetEntityResponse
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.usecases import GetEntityUseCaseImpl


class GetEntityUseCase(Protocol):
    """Protocol for the get entity use case."""

    async def execute(
        self, identifier_value: str, identifier_type: str
    ) -> GetEntityResponse:
        """Retrieve entity information by identifier."""
        ...


async def get_get_entity_use_case(
    tenant_info: TenantInfo = Depends(get_tenant_info),
) -> GetEntityUseCase:
    """Dependency injection for the get entity use case."""

    pool = await get_graph_db_pool()
    repository = AgeRepository(pool, graph_name=tenant_info.graph_name)
    return GetEntityUseCaseImpl(repository=repository)


router = APIRouter()


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
