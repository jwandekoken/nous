"""Graph database models for KuzuDB integration.

This module defines Pydantic models that represent the KuzuDB graph schema
including nodes (Entity, Identifier, Fact, Source) and relationships
(HAS_IDENTIFIER, HAS_FACT, DERIVED_FROM).
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# def datetime_encoder(dt: datetime | None) -> str | None:
#     """Encode datetime to ISO format string."""
#     return dt.isoformat() if dt else None


# Base configuration for all models
class GraphBaseModel(BaseModel):
    """Base model for all graph entities with common functionality."""

    model_config = ConfigDict(  # pyright: ignore[reportUnannotatedClassAttribute]
        from_attributes=True,
        # json_encoders={
        #     datetime: datetime_encoder,
        #     UUID: str,
        # },
    )


# Node Models
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

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, v: dict[str, Any] | None) -> dict[str, str]:  # pyright: ignore[reportExplicitAny]
        """Ensure metadata is a dictionary of strings."""
        if v is None:
            return {}
        # v is guaranteed to be dict[str, Any] at this point
        return {str(k): str(val) for k, val in v.items()}  # pyright: ignore[reportAny]


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


# Relationship Models
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


# Utility Models for API Operations
class GraphQueryResult(GraphBaseModel):
    """Result of a graph database query operation."""

    success: bool = Field(..., description="Whether the operation succeeded")
    data: list[dict[str, Any]] | None = Field(
        default_factory=list, description="Query results as list of dictionaries"
    )
    error: str | None = Field(None, description="Error message if operation failed")
    metadata: dict[str, Any] | None = Field(
        default_factory=dict, description="Additional metadata about the operation"
    )


class EntityWithRelations(GraphBaseModel):
    """Entity with its associated identifiers and facts for full representation."""

    entity: Entity
    identifiers: list[Identifier] = Field(default_factory=list)
    facts: list[dict[str, Any]] = Field(
        default_factory=list, description="Facts with relationship metadata"
    )
    primary_identifier: Identifier | None = None


# Helper Functions
def create_entity_with_identifier(
    identifier_value: str,
    identifier_type: str,
    metadata: dict[str, str] | None = None,
) -> tuple[Entity, Identifier, HasIdentifier]:
    """Helper function to create an entity with its primary identifier.

    Args:
        identifier_value: The identifier value (e.g., email)
        identifier_type: Type of identifier
        metadata: Optional entity metadata

    Returns:
        Tuple of (Entity, Identifier, HasIdentifier relationship)
    """
    entity = Entity(metadata=metadata or {})
    identifier = Identifier(value=identifier_value, type=identifier_type)
    relationship = HasIdentifier(
        from_entity_id=entity.id, to_identifier_value=identifier.value, is_primary=True
    )

    return entity, identifier, relationship


def create_fact_with_source(
    name: str,
    fact_type: str,
    source_content: str,
    source_timestamp: datetime | None = None,
) -> tuple[Fact, Source, DerivedFrom]:
    """Helper function to create a fact with its source.

    Args:
        name: Name of the fact
        fact_type: Type/category of the fact
        source_content: Content where the fact was found
        source_timestamp: When the source was created

    Returns:
        Tuple of (Fact, Source, DerivedFrom relationship)
    """
    fact_id = Fact.create_fact_id(fact_type, name)
    fact = Fact(fact_id=fact_id, name=name, type=fact_type)

    source = Source(
        content=source_content, timestamp=source_timestamp or datetime.now(timezone.utc)
    )

    relationship = DerivedFrom(from_fact_id=fact_id, to_source_id=source.id)

    return fact, source, relationship


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
