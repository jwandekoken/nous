from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.authentication import pwd_context
from app.core.authorization import is_tenant_admin
from app.core.schemas import AuthenticatedUser
from app.db.postgres.auth_session import get_auth_db_session
from app.features.auth.dtos import (
    CreateUserRequest,
    CreateUserResponse,
    DeleteUserResponse,
    GetUserResponse,
    ListUsersRequest,
    ListUsersResponse,
    UpdateUserRequest,
    UpdateUserResponse,
)
from app.features.auth.usecases.users.create_user_usecase import CreateUserUseCaseImpl
from app.features.auth.usecases.users.delete_user_usecase import DeleteUserUseCaseImpl
from app.features.auth.usecases.users.get_user_usecase import GetUserUseCaseImpl
from app.features.auth.usecases.users.list_users_usecase import ListUsersUseCaseImpl
from app.features.auth.usecases.users.update_user_usecase import UpdateUserUseCaseImpl

router = APIRouter()


class ListUsersUseCase(Protocol):
    """Protocol for the list users use case."""

    async def execute(
        self, request: ListUsersRequest, admin_user: AuthenticatedUser
    ) -> ListUsersResponse:
        """List users with pagination and filtering."""
        ...


class GetUserUseCase(Protocol):
    """Protocol for the get user use case."""

    async def execute(
        self, user_id: UUID, admin_user: AuthenticatedUser
    ) -> GetUserResponse:
        """Get a single user by ID."""
        ...


class UpdateUserUseCase(Protocol):
    """Protocol for the update user use case."""

    async def execute(
        self, user_id: UUID, request: UpdateUserRequest, admin_user: AuthenticatedUser
    ) -> UpdateUserResponse:
        """Update a user."""
        ...


class DeleteUserUseCase(Protocol):
    """Protocol for the delete user use case."""

    async def execute(
        self, user_id: UUID, admin_user: AuthenticatedUser
    ) -> DeleteUserResponse:
        """Delete a user and its associated data."""
        ...


class CreateUserUseCase(Protocol):
    """Protocol for the create user use case."""

    async def execute(
        self, request: CreateUserRequest, admin_user: AuthenticatedUser
    ) -> CreateUserResponse:
        """Create a new user within a tenant."""
        ...


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


async def get_list_users_use_case():
    """Dependency injection for the list users use case."""
    return ListUsersUseCaseImpl(
        get_db_session=get_auth_db_session,
    )


async def get_get_user_use_case():
    """Dependency injection for the get user use case."""
    return GetUserUseCaseImpl(
        get_db_session=get_auth_db_session,
    )


async def get_update_user_use_case():
    """Dependency injection for the update user use case."""
    return UpdateUserUseCaseImpl(
        password_hasher=PasswordHasherImpl(),
        get_db_session=get_auth_db_session,
    )


async def get_delete_user_use_case():
    """Dependency injection for the delete user use case."""
    return DeleteUserUseCaseImpl(
        get_db_session=get_auth_db_session,
    )


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


@router.get("/users", response_model=ListUsersResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = None,
    sort_by: str = Query("created_at", pattern="^(email|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    admin_user: AuthenticatedUser = Depends(is_tenant_admin),
    use_case: ListUsersUseCase = Depends(get_list_users_use_case),
) -> ListUsersResponse:
    """List all users within the admin's tenant with pagination and filtering.

    This endpoint allows tenant admins to:
    - Browse users within their tenant with pagination
    - Search users by email (case-insensitive)
    - Sort by email or creation date
    - Control page size (max 100)

    Only tenant admins can list users, and results are automatically scoped to their tenant.
    """
    request = ListUsersRequest(
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await use_case.execute(request, admin_user)


@router.get("/users/{user_id}", response_model=GetUserResponse)
async def get_user(
    user_id: UUID,
    admin_user: AuthenticatedUser = Depends(is_tenant_admin),
    use_case: GetUserUseCase = Depends(get_get_user_use_case),
) -> GetUserResponse:
    """Get a single user by ID.

    Only tenant admins can retrieve user details.
    The user must belong to the admin's tenant.
    """
    return await use_case.execute(user_id, admin_user)


@router.patch("/users/{user_id}", response_model=UpdateUserResponse)
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    admin_user: AuthenticatedUser = Depends(is_tenant_admin),
    use_case: UpdateUserUseCase = Depends(get_update_user_use_case),
) -> UpdateUserResponse:
    """Update a user's information.

    Only tenant admins can update user information.
    The user must belong to the admin's tenant.

    Fields that can be updated:
    - email: User's email address
    - is_active: Active status
    - role: User role
    - password: Reset user's password
    """
    return await use_case.execute(user_id, request, admin_user)


@router.delete("/users/{user_id}", response_model=DeleteUserResponse)
async def delete_user(
    user_id: UUID,
    admin_user: AuthenticatedUser = Depends(is_tenant_admin),
    use_case: DeleteUserUseCase = Depends(get_delete_user_use_case),
) -> DeleteUserResponse:
    """Delete a user and all associated data.

    This will delete:
    1. The user record
    2. All refresh tokens associated with the user

    Only tenant admins can delete users.
    The user must belong to the admin's tenant.
    """
    return await use_case.execute(user_id, admin_user)
