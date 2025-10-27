from typing import Protocol

from fastapi import APIRouter, Depends, status

from app.core.authentication import pwd_context
from app.core.authorization import is_tenant_admin
from app.core.schemas import AuthenticatedUser
from app.db.postgres.auth_session import get_auth_db_session
from app.features.auth.dtos import CreateUserRequest, CreateUserResponse
from app.features.auth.usecases.create_user_usecase import CreateUserUseCaseImpl

router = APIRouter()


class PasswordHasherImpl:
    """Wrapper for password hashing to match protocol."""

    def hash(self, secret: str | bytes, **kwargs) -> str:
        """Hash a password or secret."""
        return pwd_context.hash(secret, **kwargs)


async def get_create_user_use_case():
    """Dependency injection for the create user use case."""
    return CreateUserUseCaseImpl(
        password_hasher=PasswordHasherImpl(),
        get_db_session=get_auth_db_session,
    )


class CreateUserUseCase(Protocol):
    """Protocol for the create user use case."""

    async def execute(
        self, request: CreateUserRequest, admin_user: AuthenticatedUser
    ) -> CreateUserResponse:
        """Create a new user within a tenant."""
        ...


@router.post(
    "/users", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED
)
async def create_tenant_user(
    request: CreateUserRequest,
    admin_user: AuthenticatedUser = Depends(is_tenant_admin),
    use_case: CreateUserUseCase = Depends(get_create_user_use_case),
) -> CreateUserResponse:
    """
    Allows a TENANT_ADMIN to create a new user within their own tenant.
    """
    return await use_case.execute(request, admin_user)
