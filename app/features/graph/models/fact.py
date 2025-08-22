"""Fact models for graph database.

This module defines the Fact model for representing discrete pieces
of knowledge or named entities.
"""

from pydantic import Field, field_validator, model_validator

from .base import GraphBaseModel


class Fact(GraphBaseModel):
    """Represents a discrete piece of knowledge or named entity.

    Facts can be locations, companies, hobbies, skills, etc.
    The fact_id is a synthetic key combining type and name.
    """

    name: str = Field(..., description="The name or value of the fact")
    type: str = Field(
        ..., description="The category of fact (e.g., 'Location', 'Company', 'Skill')"
    )
    fact_id: str | None = Field(
        default=None,
        description="Synthetic primary key (e.g., 'Location:Paris')",
        # make it non-editable after creation
        frozen=True,
    )

    @field_validator("name", "type")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure name and type are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def compute_fact_id(self) -> "Fact":
        """Generate the synthetic fact_id from name and type."""
        # This code runs after 'name' and 'type' have been validated.
        # 'self' here is the complete model, so self.name and self.type are safe to access.
        if self.name and self.type:
            # Pydantic v2 protects frozen fields, so we use `object.__setattr__`
            # to assign the computed value.
            object.__setattr__(
                self, "fact_id", self.create_fact_id(self.type, self.name)
            )
        return self

    @classmethod
    def create_fact_id(cls, fact_type: str, name: str) -> str:
        """Helper method to create a synthetic fact_id."""
        return f"{fact_type}:{name}"
