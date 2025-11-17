"""Facts management route handler."""

from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, Path

from app.core.authorization import TenantInfo, get_tenant_info, is_tenant_admin
from app.core.schemas import AuthenticatedUser
from app.db.postgres.graph_connection import get_graph_db_pool
from app.features.graph.dtos.knowledge_dto import RemoveFactFromEntityResponse
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.usecases.remove_fact_usecase import (
    RemoveFactFromEntityUseCaseImpl,
)


class RemoveFactFromEntityUseCase(Protocol):
    """Protocol for the remove fact from entity use case."""

    async def execute(
        self, entity_id: UUID, fact_id: str
    ) -> RemoveFactFromEntityResponse:
        """Remove a fact from an entity."""
        ...


async def get_remove_fact_use_case(
    tenant_info: TenantInfo = Depends(get_tenant_info),
) -> RemoveFactFromEntityUseCase:
    """Dependency injection for the remove fact use case."""
    pool = await get_graph_db_pool()
    repository = AgeRepository(pool, graph_name=tenant_info.graph_name)
    return RemoveFactFromEntityUseCaseImpl(repository=repository)


router = APIRouter()


@router.delete(
    "/entities/{entity_id}/facts/{fact_id}",
    response_model=RemoveFactFromEntityResponse,
    status_code=200,
)
async def remove_fact_from_entity(
    entity_id: UUID = Path(..., description="The entity's unique identifier"),
    fact_id: str = Path(
        ..., description="The fact's synthetic ID (e.g., 'Location:Paris')"
    ),
    use_case: RemoveFactFromEntityUseCase = Depends(get_remove_fact_use_case),
    _admin_user: AuthenticatedUser = Depends(is_tenant_admin),
) -> RemoveFactFromEntityResponse:
    """Remove a fact from an entity.

    This endpoint removes all HAS_FACT relationships between the specified entity
    and fact. If the fact is only used by this entity, the fact itself and its
    source (if not shared) will also be deleted from the graph.

    Args:
        entity_id: UUID of the entity
        fact_id: Synthetic fact ID (format: 'Type:Name', e.g., 'Location:Paris')

    Returns:
        RemoveFactFromEntityResponse with operation result

    Raises:
        404: If the entity-fact relationship doesn't exist
    """
    return await use_case.execute(entity_id=entity_id, fact_id=fact_id)
