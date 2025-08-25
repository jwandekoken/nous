"""Graph API routes package - separated by entity type."""

from .entities import router as entities_router
from .entity_facts import router as entity_facts_router
from .facts import router as facts_router

__all__ = [
    "entities_router",
    "entity_facts_router",
    "facts_router",
]
