"""Utility models and helper functions for graph database.

This module contains utility models and helper functions that don't
fit into the main model categories.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import Field

from .base_model import GraphBaseModel
from .entity_model import Entity
from .fact_model import Fact
from .identifier_model import HasIdentifier, Identifier
from .source_model import DerivedFrom, Source


# Utility Models for API Operations
class GraphQueryResult(GraphBaseModel):
    """Result of a graph database query operation."""

    success: bool = Field(..., description="Whether the operation succeeded")
    data: list[dict[str, Any]] | None = Field(
        default_factory=list, description="Query results as list of dictionaries"
    )
    error: str | None = Field(None, description="Error message if operation failed")
    metadata: dict[str, Any] | None = Field(
        default_factory=dict, description="Additional metadata about the operation"
    )


class EntityWithRelations(GraphBaseModel):
    """Entity with its associated identifiers and facts for full representation."""

    entity: Entity
    identifiers: list[Identifier] = Field(default_factory=list)
    facts: list[dict[str, Any]] = Field(
        default_factory=list, description="Facts with relationship metadata"
    )
    primary_identifier: Identifier | None = None


# Helper Functions
def create_entity_with_identifier(
    identifier_value: str,
    identifier_type: str,
    metadata: dict[str, str] | None = None,
) -> tuple[Entity, Identifier, HasIdentifier]:
    """Helper function to create an entity with its primary identifier.

    Args:
        identifier_value: The identifier value (e.g., email)
        identifier_type: Type of identifier
        metadata: Optional entity metadata

    Returns:
        Tuple of (Entity, Identifier, HasIdentifier relationship)
    """
    entity = Entity(metadata=metadata or {})
    identifier = Identifier(value=identifier_value, type=identifier_type)
    relationship = HasIdentifier(
        from_entity_id=entity.id, to_identifier_value=identifier.value, is_primary=True
    )

    return entity, identifier, relationship


def create_fact_with_source(
    name: str,
    fact_type: str,
    source_content: str,
    source_timestamp: datetime | None = None,
) -> tuple[Fact, Source, DerivedFrom]:
    """Helper function to create a fact with its source.

    Args:
        name: Name of the fact
        fact_type: Type/category of the fact
        source_content: Content where the fact was found
        source_timestamp: When the source was created

    Returns:
        Tuple of (Fact, Source, DerivedFrom relationship)
    """
    fact_id = Fact.create_fact_id(fact_type, name)
    fact = Fact(fact_id=fact_id, name=name, type=fact_type)

    source = Source(
        content=source_content, timestamp=source_timestamp or datetime.now(timezone.utc)
    )

    relationship = DerivedFrom(from_fact_id=fact_id, to_source_id=source.id)

    return fact, source, relationship
