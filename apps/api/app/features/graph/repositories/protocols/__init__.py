"""Repository protocols for the graph feature."""

from .graph_repository import (
    AddFactToEntityResult,
    CreateEntityResult,
    EntityWithRelations,
    FactWithOptionalSource,
    FactWithSource,
    FindEntityByIdResult,
    FindEntityResult,
    GraphRepository,
    IdentifierWithRelationship,
)
from .vector_repository import SemanticSearchResult, VectorRepository

__all__ = [
    # Graph protocol and types
    "GraphRepository",
    "AddFactToEntityResult",
    "CreateEntityResult",
    "EntityWithRelations",
    "FactWithOptionalSource",
    "FactWithSource",
    "FindEntityByIdResult",
    "FindEntityResult",
    "IdentifierWithRelationship",
    # Vector protocol and types
    "VectorRepository",
    "SemanticSearchResult",
]
