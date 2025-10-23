"""Signup route handler."""

from typing import Protocol

from fastapi import APIRouter, Depends

from app.core.authentication import AuthenticatedUser, pwd_context
from app.core.authorization import is_super_admin
from app.db.postgres.auth_session import get_auth_db_session
from app.db.postgres.graph_connection import get_graph_db_pool
from app.features.auth.dtos import SignupRequest, SignupResponse
from app.features.auth.usecases.signup_tenant_usecase import SignupTenantUseCaseImpl


class PasswordHasherImpl:
    """Wrapper for password hashing to match protocol."""

    def hash(self, secret: str | bytes, **kwargs) -> str:
        """Hash a password or secret."""
        return pwd_context.hash(secret, **kwargs)


async def get_signup_tenant_use_case():
    """Dependency injection for the signup tenant use case."""
    return SignupTenantUseCaseImpl(
        password_hasher=PasswordHasherImpl(),
        get_db_session=get_auth_db_session,
        get_db_pool=get_graph_db_pool,
    )


class SignupTenantUseCase(Protocol):
    """Protocol for the signup tenant use case."""

    async def execute(self, request: SignupRequest) -> SignupResponse:
        """Create a new tenant with user and graph."""
        ...


router = APIRouter()


@router.post("/create_tenant", response_model=SignupResponse)
async def create_tenant(
    request: SignupRequest,
    use_case: SignupTenantUseCase = Depends(get_signup_tenant_use_case),
    _: AuthenticatedUser = Depends(is_super_admin),
) -> SignupResponse:
    """Create a new tenant with an initial user and AGE graph.

    This endpoint creates:
    1. A new tenant record
    2. An initial user for the tenant
    3. A dedicated Apache AGE graph for the tenant
    """
    return await use_case.execute(request)
