"""Identifier models for graph database.

This module defines the Identifier model for external identifiers
like email addresses, phone numbers, usernames, etc.
"""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import Field, field_validator
from typing_extensions import override

from .base_model import GraphBaseModel


class Identifier(GraphBaseModel):
    """Represents an external identifier for an entity.

    Examples: email addresses, phone numbers, usernames, etc.
    The value serves as the primary key for uniqueness.
    """

    value: str = Field(
        ..., description="The identifier value (e.g., 'user@example.com')"
    )
    type: str = Field(
        ..., description="Type of identifier (e.g., 'email', 'phone', 'username')"
    )

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        """Ensure identifier value is not empty and properly formatted."""
        if not v or not v.strip():
            raise ValueError("Identifier value cannot be empty")
        return v.strip()

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Ensure identifier type is valid."""
        valid_types = {"email", "phone", "username", "uuid", "social_id"}
        if v not in valid_types:
            raise ValueError(f"Identifier type must be one of: {valid_types}")
        return v


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

    @override
    def to_db_timestamp(self) -> str:
        """Format this relationship's created_at timestamp for database storage.

        Returns:
            Formatted timestamp string for KuzuDB
        """
        return self.created_at.strftime("%Y-%m-%d %H:%M:%S")
