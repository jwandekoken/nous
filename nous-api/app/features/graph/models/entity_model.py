"""Entity models for graph database.

This module defines the Entity model and related entity-specific functionality.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import Field

from .base_model import GraphBaseModel


class Entity(GraphBaseModel):
    """Represents a canonical entity in the graph database.

    The Entity is the central node that represents a real-world subject
    (e.g., a person, organization, or concept) with a stable UUID.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique system identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this entity was created in the system",
    )
    metadata: dict[str, str] | None = Field(
        default_factory=dict, description="Flexible metadata as key-value pairs"
    )
