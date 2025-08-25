"""Entity-related DTOs for graph database API.

This module defines request and response models for entity operations.
"""

from typing import Any

from pydantic import BaseModel, Field

from ..models.base import GraphBaseModel
from ..models.entity import Entity
from ..models.identifier import Identifier


class CreateEntityRequest(BaseModel):
    """Request model for creating a new entity."""

    identifier_value: str = Field(
        ..., description="The identifier value (e.g., email, username)"
    )
    identifier_type: str = Field(
        ..., description="Type of identifier (email, phone, username, etc.)"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata for the entity"
    )


class CreateEntityResponse(GraphBaseModel):
    """Response model for entity creation."""

    entity: Entity = Field(..., description="The created entity")
    identifiers: list[Identifier] = Field(
        ..., description="All identifiers for the entity"
    )
    primary_identifier: Identifier = Field(..., description="The primary identifier")


class GetEntityResponse(GraphBaseModel):
    """Response model for entity retrieval."""

    entity: Entity = Field(..., description="The entity")
    identifiers: list[Identifier] = Field(
        ..., description="All identifiers for the entity"
    )
    facts: list[dict[str, Any]] = Field(
        ..., description="Facts associated with the entity"
    )
    sources: list = Field(..., description="Sources for the facts")


class SearchEntitiesResponse(GraphBaseModel):
    """Response model for entity search."""

    entities: list[dict[str, Any]] = Field(
        ..., description="List of matching entities with their identifiers"
    )
    total_count: int = Field(..., description="Total number of entities found")
