"""Protocol definition and types for graph repository operations."""

from typing import Protocol, TypedDict

from app.features.graph.models import (
    DerivedFrom,
    Entity,
    Fact,
    HasFact,
    HasIdentifier,
    Identifier,
    Source,
)


class CreateEntityResult(TypedDict):
    """Result of creating a new entity with its identifier and relationship."""

    entity: Entity
    identifier: Identifier
    relationship: HasIdentifier


class FactWithSource(TypedDict):
    """A fact with its associated source information."""

    fact: Fact
    source: Source | None
    relationship: HasFact


class FactWithOptionalSource(TypedDict):
    """A fact with its optionally associated source information."""

    fact: Fact
    source: Source | None


class IdentifierWithRelationship(TypedDict):
    """Groups the identifier used for the lookup with its relationship to the entity."""

    identifier: Identifier
    relationship: HasIdentifier


class FindEntityResult(TypedDict):
    """Result of finding an entity by its identifier, including facts and sources."""

    entity: Entity
    identifier: IdentifierWithRelationship
    facts_with_sources: list[FactWithSource]


class FindEntityByIdResult(TypedDict):
    """Result of finding an entity by its ID, including facts and sources."""

    entity: Entity
    identifier: IdentifierWithRelationship | None
    facts_with_sources: list[FactWithSource]


class EntityWithRelations(TypedDict):
    """Complete entity data with all its relationships and associated objects."""

    entity: Entity
    identifiers: list[Identifier]
    facts_with_sources: list[FactWithSource]


class AddFactToEntityResult(TypedDict):
    """Result of adding a fact with source to an entity."""

    fact: Fact
    source: Source
    has_fact_relationship: HasFact
    derived_from_relationship: DerivedFrom


class GraphRepository(Protocol):
    """Protocol for a generic graph repository.

    This protocol defines the interface for graph database operations.
    Implementations include AgeRepository for Apache AGE.
    """

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
