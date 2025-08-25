"""Source models for graph database.

This module defines the Source model for tracking the origin
of information in the graph.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from .base import GraphBaseModel


class Source(GraphBaseModel):
    """Represents the origin of information in the graph.

    Sources track where facts came from (chat messages, emails, documents, etc.)
    enabling traceability and data provenance.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique system identifier")
    content: str = Field(..., description="The original content/source text")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Real-world timestamp when the source was created",
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure content is not empty."""
        if not v or not v.strip():
            raise ValueError("Source content cannot be empty")
        return v.strip()


class DerivedFrom(GraphBaseModel):
    """Relationship connecting a Fact to its Source.

    This enables traceability by linking facts back to their origins,
    answering the question: "How do we know this fact?"
    """

    from_fact_id: str = Field(..., description="Fact that was derived")
    to_source_id: UUID = Field(..., description="Source where the fact originated")
