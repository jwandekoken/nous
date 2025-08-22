"""Identifier models for graph database.

This module defines the Identifier model for external identifiers
like email addresses, phone numbers, usernames, etc.
"""

from pydantic import Field, field_validator

from .base import GraphBaseModel


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
