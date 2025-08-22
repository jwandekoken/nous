"""Relationship models for graph database.

This module defines all relationship models that connect nodes
in the graph database.
"""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import Field, field_validator

from .base import GraphBaseModel


class HasIdentifier(GraphBaseModel):
    """Relationship connecting an Entity to its external Identifiers.

    This relationship allows entities to have multiple identifiers
    while maintaining a canonical UUID as the primary key.
    """

    from_entity_id: UUID = Field(..., description="Entity that owns the identifier")
    to_identifier_value: str = Field(
        ..., description="Identifier value being connected"
    )
    is_primary: bool = Field(
        default=False,
        description="Whether this is the primary identifier for the entity",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this relationship was established",
    )


class HasFact(GraphBaseModel):
    """Relationship connecting an Entity to a Fact it possesses.

    The verb provides semantic context about how the entity relates to the fact.
    """

    from_entity_id: UUID = Field(..., description="Entity that possesses the fact")
    to_fact_id: str = Field(..., description="Fact being connected")
    verb: str = Field(
        ..., description="Semantic relationship (e.g., 'lives_in', 'works_at')"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
        description="Confidence level of this fact (0.0 to 1.0)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this relationship was established",
    )

    @field_validator("verb")
    @classmethod
    def validate_verb(cls, v: str) -> str:
        """Ensure verb is a valid semantic relationship."""
        if not v or not v.strip():
            raise ValueError("Verb cannot be empty")
        return v.strip().lower()


class DerivedFrom(GraphBaseModel):
    """Relationship connecting a Fact to its Source.

    This enables traceability by linking facts back to their origins,
    answering the question: "How do we know this fact?"
    """

    from_fact_id: str = Field(..., description="Fact that was derived")
    to_source_id: UUID = Field(..., description="Source where the fact originated")
