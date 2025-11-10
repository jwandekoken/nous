"""Knowledge assimilation DTOs for API requests and responses.

This module defines Data Transfer Objects for the knowledge assimilation API.
"""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field


class EntityDto(BaseModel):
    """DTO for Entity API responses."""

    id: UUID = Field(..., description="Unique system identifier")
    created_at: datetime = Field(
        ..., description="When this entity was created in the system"
    )
    metadata: dict[str, str] | None = Field(
        default_factory=dict, description="Flexible metadata as key-value pairs"
    )


class FactDto(BaseModel):
    """DTO for Fact API responses."""

    name: str = Field(..., description="The name or value of the fact")
    type: str = Field(
        ..., description="The category of fact (e.g., 'Location', 'Company', 'Skill')"
    )
    fact_id: str | None = Field(
        default=None, description="Synthetic primary key (e.g., 'Location:Paris')"
    )


class ExtractedFactDto(BaseModel):
    """DTO for facts extracted from text content."""

    name: str = Field(..., description="The name or value of the extracted fact")
    type: str = Field(
        ..., description="The category of the fact (e.g., 'Location', 'Profession')"
    )
    verb: str = Field(
        ..., description="The semantic verb connecting the entity to the fact"
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence level of the extracted fact (0.0 to 1.0)",
    )


class IdentifierDto(BaseModel):
    """DTO for an Identifier."""

    value: str = Field(
        ..., description="The identifier value (e.g., 'user@example.com')"
    )
    type: str = Field(
        ..., description="Type of identifier (e.g., 'email', 'phone', 'username')"
    )


class AssimilateKnowledgeRequest(BaseModel):
    """Request to process content and associate facts with an entity."""

    identifier: IdentifierDto = Field(
        ..., description="The entity's external identifier."
    )
    content: str = Field(..., description="The textual content to process.")
    timestamp: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The real-world timestamp of the content's creation.",
    )
    history: list[str] | None = Field(
        default=None,
        description="Optional list of previous conversational turns for context.",
    )


class SourceDto(BaseModel):
    """DTO for a Source."""

    id: UUID = Field(..., description="Unique system identifier")
    content: str = Field(..., description="The original content/source text")
    timestamp: datetime = Field(
        ..., description="Real-world timestamp when the source was created"
    )


class HasFactDto(BaseModel):
    """DTO for the relationship between an Entity and a Fact."""

    verb: str = Field(
        ..., description="Semantic relationship (e.g., 'lives_in', 'works_at')"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence level of this fact (0.0 to 1.0)",
    )
    created_at: datetime = Field(
        ..., description="When this relationship was established"
    )


class AssimilatedFactDto(BaseModel):
    """DTO grouping a fact with its relationship to the entity."""

    fact: FactDto = Field(..., description="The extracted fact")
    relationship: HasFactDto = Field(
        ..., description="The relationship between the entity and the fact"
    )


class AssimilateKnowledgeResponse(BaseModel):
    """Response after successfully assimilating knowledge."""

    entity: EntityDto = Field(
        ..., description="The entity the knowledge was assimilated for."
    )
    source: SourceDto = Field(..., description="The source created from the content.")
    assimilated_facts: list[AssimilatedFactDto] = Field(
        ...,
        description="A list of facts extracted with their relationships to the entity.",
    )


class HasIdentifierDto(BaseModel):
    """DTO for the relationship between an Entity and an Identifier."""

    is_primary: bool = Field(
        ..., description="Whether this is the primary identifier for the entity"
    )
    created_at: datetime = Field(
        ..., description="When this relationship was established"
    )


class IdentifierWithRelationshipDto(BaseModel):
    """DTO grouping an identifier with its relationship to the entity."""

    identifier: IdentifierDto
    relationship: HasIdentifierDto


class FactWithSourceDto(BaseModel):
    """DTO grouping a fact with its relationship and source."""

    fact: FactDto
    relationship: HasFactDto
    source: SourceDto | None = Field(
        None, description="The source of the fact, if available."
    )


class GetEntityResponse(BaseModel):
    """Response for getting an entity by identifier."""

    entity: EntityDto
    identifier: IdentifierWithRelationshipDto
    facts: list[FactWithSourceDto]


class GetEntitySummaryResponse(BaseModel):
    """Response for getting a natural language summary of entity data."""

    summary: str = Field(
        ...,
        description="Natural language summary of the entity's facts and relationships, optimized for LLM consumption",
    )
