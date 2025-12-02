from typing import Protocol

from fastapi import APIRouter, Depends

from app.core.authentication import pwd_context
from app.db.postgres.auth_session import get_auth_db_session
from app.features.auth.dtos import (
    SetupAdminRequest,
    SetupAdminResponse,
    SetupRequiredResponse,
)
from app.features.auth.usecases.setup.check_setup_required_usecase import (
    CheckSetupRequiredUseCaseImpl,
)
from app.features.auth.usecases.setup.setup_admin_usecase import SetupAdminUseCaseImpl


# Define Protocols
class CheckSetupRequiredUseCase(Protocol):
    """Protocol for the check setup required use case."""

    async def execute(self) -> SetupRequiredResponse:
        """Check if the application requires initial setup."""
        ...


class SetupAdminUseCase(Protocol):
    """Protocol for the setup admin use case."""

    async def execute(self, request: SetupAdminRequest) -> SetupAdminResponse:
        """Create the first super admin user."""
        ...


class PasswordHasherImpl:
    """Wrapper for password hashing to match protocol."""

    def hash(self, secret: str | bytes, **kwargs) -> str:
        """Hash a password or secret."""
        return pwd_context.hash(secret, **kwargs)


# Dependency Injection
async def get_check_setup_required_use_case() -> CheckSetupRequiredUseCase:
    """Dependency injection for the check setup required use case."""
    return CheckSetupRequiredUseCaseImpl(
        get_db_session=get_auth_db_session,
    )


async def get_setup_admin_use_case() -> SetupAdminUseCase:
    """Dependency injection for the setup admin use case."""
    return SetupAdminUseCaseImpl(
        password_hasher=PasswordHasherImpl(),
        get_db_session=get_auth_db_session,
    )


router = APIRouter()


@router.get("/setup-required", response_model=SetupRequiredResponse)
async def check_setup_required(
    use_case: CheckSetupRequiredUseCase = Depends(get_check_setup_required_use_case),
) -> SetupRequiredResponse:
    """Check if the application requires initial setup (no super admin exists)."""
    return await use_case.execute()


@router.post("/setup-admin", response_model=SetupAdminResponse)
async def setup_admin(
    request: SetupAdminRequest,
    use_case: SetupAdminUseCase = Depends(get_setup_admin_use_case),
) -> SetupAdminResponse:
    """Create the first super admin user. Only allowed if no super admin exists."""
    return await use_case.execute(request)
