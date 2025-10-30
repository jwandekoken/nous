"""Use case for creating a new user within a tenant."""

from contextlib import AbstractAsyncContextManager
from typing import Callable, Protocol

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import AuthenticatedUser, UserRole
from app.features.auth.dtos import CreateUserRequest, CreateUserResponse
from app.features.auth.models import User


class PasswordHasher(Protocol):
    """Protocol for password hashing operations."""

    def hash(self, secret: str | bytes, **kwargs) -> str:
        """Hash a password or secret."""
        ...


class CreateUserUseCaseImpl:
    """Implementation of the create user use case."""

    def __init__(
        self,
        password_hasher: PasswordHasher,
        get_db_session: Callable[[], AbstractAsyncContextManager[AsyncSession]],
    ):
        """Initialize the use case with dependencies.

        Args:
            password_hasher: Service for hashing passwords
            get_db_session: Function to get database session
        """
        self.password_hasher = password_hasher
        self.get_auth_db_session = get_db_session

    async def execute(
        self, request: CreateUserRequest, admin_user: AuthenticatedUser
    ) -> CreateUserResponse:
        """Create a new user within the admin's tenant.

        Args:
            request: The user creation request containing user details
            admin_user: The authenticated admin user performing the action

        Returns:
            Response with success message and user ID

        Raises:
            HTTPException: With appropriate status codes for validation and creation errors
        """
        # Validate admin has a tenant
        if admin_user.tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin has no tenant",
            )

        # Hash password
        hashed_password = self.password_hasher.hash(request.password)

        async with self.get_auth_db_session() as session:
            try:
                # Create user
                new_user = User(
                    email=request.email,
                    hashed_password=hashed_password,
                    tenant_id=admin_user.tenant_id,
                    role=UserRole.TENANT_USER,
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)

                return CreateUserResponse(
                    message="User created successfully",
                    user_id=str(new_user.id),
                    email=new_user.email,
                    role=UserRole.TENANT_USER,
                )

            except IntegrityError:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists in the tenant",
                )
            except Exception as e:
                await session.rollback()
                # Log the error (in production, use proper logging)
                print(f"Create user error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user",
                )
