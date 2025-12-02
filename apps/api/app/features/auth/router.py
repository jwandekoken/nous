"""Authentication and authorization API routes."""

from fastapi import APIRouter

from app.features.auth.routes.api_keys import router as api_keys_router
from app.features.auth.routes.login import router as login_router
from app.features.auth.routes.setup import router as setup_router
from app.features.auth.routes.tenants import router as tenants_router
from app.features.auth.routes.users import router as users_router

router = APIRouter(prefix="/auth", tags=["auth"])

# Include all route handlers
router.include_router(tenants_router)
router.include_router(login_router)
router.include_router(api_keys_router)
router.include_router(users_router)
router.include_router(setup_router)
