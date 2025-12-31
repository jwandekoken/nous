"""Graph repositories package."""

from .age_repository import AgeRepository
from .protocols import (
    AddFactToEntityResult,
    CreateEntityResult,
    EntityWithRelations,
    FactWithOptionalSource,
    FactWithSource,
    FindEntityByIdResult,
    FindEntityResult,
    GraphRepository,
    IdentifierWithRelationship,
    SemanticSearchResult,
    VectorRepository,
)
from .qdrant_repository import QdrantRepository

__all__ = [
    # Graph implementation
    "AgeRepository",
    # Vector implementation
    "QdrantRepository",
    # Protocol and types (from protocols/)
    "GraphRepository",
    "VectorRepository",
    "AddFactToEntityResult",
    "CreateEntityResult",
    "EntityWithRelations",
    "FactWithOptionalSource",
    "FactWithSource",
    "FindEntityByIdResult",
    "FindEntityResult",
    "IdentifierWithRelationship",
    "SemanticSearchResult",
]
