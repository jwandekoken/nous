"""Graph API routes package - separated by entity type."""

from .entities_routes import router as entities_router
from .facts_routes import router as facts_router

__all__ = [
    "entities_router",
    "facts_router",
]
