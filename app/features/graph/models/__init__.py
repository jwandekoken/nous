"""Graph database models package.

This package contains all Pydantic models for the KuzuDB graph schema
including nodes, relationships, API models, and utility functions.
"""

# Base models
# API models
from .api import (
    AddFactRequest,
    AddFactResponse,
    CreateEntityRequest,
    CreateEntityResponse,
    GetEntityResponse,
    GetFactResponse,
    SearchEntitiesResponse,
)
from .base import GraphBaseModel

# Node models
from .entity import Entity
from .fact import Fact
from .identifier import Identifier

# Relationship models
from .relationships import DerivedFrom, HasFact, HasIdentifier
from .source import Source

# Utility models and helper functions
from .utils import (
    EntityWithRelations,
    GraphQueryResult,
    create_entity_with_identifier,
    create_fact_with_source,
)

__all__ = [
    # Base models
    "GraphBaseModel",
    # Node models
    "Entity",
    "Identifier",
    "Fact",
    "Source",
    # Relationship models
    "HasIdentifier",
    "HasFact",
    "DerivedFrom",
    # Utility models
    "GraphQueryResult",
    "EntityWithRelations",
    # API models
    "CreateEntityRequest",
    "CreateEntityResponse",
    "AddFactRequest",
    "AddFactResponse",
    "GetEntityResponse",
    "SearchEntitiesResponse",
    "GetFactResponse",
    # Helper functions
    "create_entity_with_identifier",
    "create_fact_with_source",
]
