"""Type definitions for graph repository operations."""

from typing import TypedDict

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
