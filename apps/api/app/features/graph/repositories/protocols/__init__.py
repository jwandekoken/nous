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

__all__ = [
    "GraphRepository",
    "AddFactToEntityResult",
    "CreateEntityResult",
    "EntityWithRelations",
    "FactWithOptionalSource",
    "FactWithSource",
    "FindEntityByIdResult",
    "FindEntityResult",
    "IdentifierWithRelationship",
]
