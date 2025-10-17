"""Graph database models package.

This package contains all Pydantic models for the KuzuDB graph schema
including nodes, relationships, API models, and utility functions.
"""

# Base models
from .base_model import GraphBaseModel

# Node models
from .entity_model import Entity
from .fact_model import Fact, HasFact
from .identifier_model import HasIdentifier, Identifier

# Relationship models
from .source_model import DerivedFrom, Source

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
    # Helper functions
    "create_entity_with_identifier",
    "create_fact_with_source",
]
