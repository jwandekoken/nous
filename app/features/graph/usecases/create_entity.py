"""Create entity usecase - handles entity creation business logic."""

from typing import Any

from app.features.graph.models import (
    Entity,
    Identifier,
    create_entity_with_identifier,
)
from app.features.graph.repository import GraphRepository


class CreateEntityUsecase:
    """Business logic for creating entities."""

    def __init__(self, repo: GraphRepository):
        self.repo = repo

    async def execute(
        self,
        identifier_value: str,
        identifier_type: str,
        metadata: dict[str, Any] | None,
    ) -> tuple[Entity, Identifier]:
        """Execute entity creation with validation and business rules."""
        entity, identifier, relationship = create_entity_with_identifier(
            identifier_value=identifier_value,
            identifier_type=identifier_type,
            metadata=metadata,
        )

        success = await self.repo.create_entity(entity, identifier, relationship)
        if not success:
            raise ValueError("Failed to persist entity in the database.")

        return entity, identifier
