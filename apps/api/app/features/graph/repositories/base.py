"""Base classes and protocols for graph repositories."""

from typing import Protocol

from app.features.graph.models import Entity, Fact, HasIdentifier, Identifier, Source
from app.features.graph.repositories.types import (
    AddFactToEntityResult,
    CreateEntityResult,
    FactWithOptionalSource,
    FindEntityByIdResult,
    FindEntityResult,
)


class GraphRepository(Protocol):
    """Protocol for a generic graph repository."""

    async def create_entity(
        self, entity: Entity, identifier: Identifier, relationship: HasIdentifier
    ) -> CreateEntityResult:
        """Create a new entity with an identifier."""
        ...

    async def find_entity_by_identifier(
        self, identifier_value: str, identifier_type: str
    ) -> FindEntityResult | None:
        """Find an entity by its identifier."""
        ...

    async def find_entity_by_id(self, entity_id: str) -> FindEntityByIdResult | None:
        """Find an entity by its ID."""
        ...

    async def delete_entity_by_id(self, entity_id: str) -> bool:
        """Delete an entity by its ID."""
        ...

    async def add_fact_to_entity(
        self,
        entity_id: str,
        fact: Fact,
        source: Source,
        verb: str,
        confidence_score: float = 1.0,
    ) -> AddFactToEntityResult:
        """Add a fact to an entity."""
        ...

    async def find_fact_by_id(self, fact_id: str) -> FactWithOptionalSource | None:
        """Find a fact by its ID."""
        ...

    async def remove_fact_from_entity(self, entity_id: str, fact_id: str) -> bool:
        """Remove a fact from an entity. Returns True if deleted, False otherwise."""
        ...
