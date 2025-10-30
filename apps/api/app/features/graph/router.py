"""Graph database API routes - main router that includes all entity-specific route modules."""

from fastapi import APIRouter, Depends

from app.core.authorization import get_tenant_info
from app.features.graph.routes.assimilate import router as assimilate_router
from app.features.graph.routes.lookup import router as lookup_router

router = APIRouter(
    prefix="/graph",
    tags=["graph"],
    dependencies=[Depends(get_tenant_info)],
)

# Include all route handlers
router.include_router(assimilate_router)
router.include_router(lookup_router)
