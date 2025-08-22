"""Get entity usecase - handles entity retrieval business logic."""

from typing import Any
from uuid import UUID

from app.features.graph.repository import GraphRepository


class GetEntityUsecase:
    """Business logic for retrieving entities."""

    def __init__(self, repo: GraphRepository):
        self.repo = repo

    async def execute(self, entity_id: UUID) -> dict[str, Any] | None:
        """Execute entity retrieval with business rules."""
        entity_data = await self.repo.find_entity_by_id(entity_id)

        if not entity_data:
            return None

        # Apply any business logic transformations here
        return entity_data
