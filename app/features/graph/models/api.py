"""API request and response models for graph database.

This module defines all request/response models for the graph database API.
"""

from typing import Any

from pydantic import BaseModel, Field

from .base import GraphBaseModel
from .entity import Entity
from .fact import Fact
from .identifier import Identifier
from .relationships import HasFact
from .source import Source


# API Request/Response Models
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


class AddFactRequest(BaseModel):
    """Request model for adding a fact to an entity."""

    fact_name: str = Field(..., description="Name of the fact")
    fact_type: str = Field(..., description="Type/category of the fact")
    verb: str = Field(..., description="Semantic relationship verb")
    source_content: str = Field(..., description="Source content where fact was found")
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence level of this fact (0.0 to 1.0)",
    )
    source_timestamp: str | None = Field(
        default=None, description="ISO format timestamp when source was created"
    )


class AddFactResponse(GraphBaseModel):
    """Response model for adding a fact."""

    message: str = Field(
        default="Fact added successfully", description="Success message"
    )
    fact: Fact = Field(..., description="The created fact")
    source: Source = Field(..., description="The source of the fact")
    relationship: HasFact = Field(
        ..., description="The relationship between entity and fact"
    )


class GetEntityResponse(GraphBaseModel):
    """Response model for entity retrieval."""

    entity: Entity = Field(..., description="The entity")
    identifiers: list[Identifier] = Field(
        ..., description="All identifiers for the entity"
    )
    facts: list[dict[str, Any]] = Field(
        ..., description="Facts associated with the entity"
    )
    sources: list[Source] = Field(..., description="Sources for the facts")


class SearchEntitiesResponse(GraphBaseModel):
    """Response model for entity search."""

    entities: list[dict[str, Any]] = Field(
        ..., description="List of matching entities with their identifiers"
    )
    total_count: int = Field(..., description="Total number of entities found")


class GetFactResponse(GraphBaseModel):
    """Response model for fact retrieval."""

    fact: Fact = Field(..., description="The fact")
    source: Source | None = Field(None, description="Source of the fact")
    entities: list[Entity] = Field(
        ..., description="Entities associated with this fact"
    )
