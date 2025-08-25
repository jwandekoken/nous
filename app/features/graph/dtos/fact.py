"""Fact-related DTOs for graph database API.

This module defines request and response models for fact operations.
"""

from pydantic import BaseModel, Field

from ..models.base import GraphBaseModel
from ..models.entity import Entity
from ..models.fact import Fact, HasFact
from ..models.source import Source


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


class GetFactResponse(GraphBaseModel):
    """Response model for fact retrieval."""

    fact: Fact = Field(..., description="The fact")
    source: Source | None = Field(None, description="Source of the fact")
    entities: list[Entity] = Field(
        ..., description="Entities associated with this fact"
    )
