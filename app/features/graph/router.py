"""Graph database API routes - main router that includes all entity-specific route modules."""

from fastapi import APIRouter

from app.features.graph.routes import entities_router, facts_router

router = APIRouter(prefix="/graph", tags=["graph"])

# Include all entity-specific route modules
router.include_router(entities_router)
router.include_router(facts_router)
