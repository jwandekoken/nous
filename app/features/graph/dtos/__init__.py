"""DTOs for graph database API.

This module re-exports all Data Transfer Objects for convenient importing.
"""

from .entity import (
    CreateEntityRequest,
    CreateEntityResponse,
    GetEntityResponse,
    SearchEntitiesResponse,
)
from .fact import (
    AddFactRequest,
    AddFactResponse,
    GetFactResponse,
)

__all__ = [
    # Entity DTOs
    "CreateEntityRequest",
    "CreateEntityResponse",
    "GetEntityResponse",
    "SearchEntitiesResponse",
    # Fact DTOs
    "AddFactRequest",
    "AddFactResponse",
    "GetFactResponse",
]
