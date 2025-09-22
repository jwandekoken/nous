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


class IdentifierPayload(BaseModel):
    """Payload for identifying an entity via an external identifier."""

    type: str = Field(..., description="Type of identifier (e.g., 'email', 'phone')")
    value: str = Field(
        ..., description="The identifier value (e.g., 'user@example.com')"
    )


class AssimilateKnowledgeRequest(BaseModel):
    """Request to process content and associate facts with an entity."""

    identifier: IdentifierPayload = Field(
        ..., description="The entity's external identifier."
    )
    content: str = Field(..., description="The textual content to process.")
    timestamp: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The real-world timestamp of the content's creation.",
    )


class SourceDto(BaseModel):
    """DTO for a Source."""

    id: UUID = Field(..., description="Unique system identifier")
    content: str = Field(..., description="The original content/source text")
    timestamp: datetime = Field(
        ..., description="Real-world timestamp when the source was created"
    )


class AssimilateKnowledgeResponse(BaseModel):
    """Response after successfully assimilating knowledge."""

    entity: EntityDto = Field(
        ..., description="The entity the knowledge was assimilated for."
    )
    source: SourceDto = Field(..., description="The source created from the content.")
    extracted_facts: list[FactDto] = Field(
        ..., description="A list of facts extracted and stored."
    )
