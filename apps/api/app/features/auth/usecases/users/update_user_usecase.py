"""Use case for updating a user."""

from contextlib import AbstractAsyncContextManager
from typing import Callable, Protocol
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.schemas import AuthenticatedUser
from app.features.auth.dtos import UpdateUserRequest, UpdateUserResponse
from app.features.auth.models import User


class PasswordHasher(Protocol):
    """Protocol for password hashing operations."""

    def hash(self, secret: str | bytes, **kwargs) -> str:
        """Hash a password or secret."""
        ...


class UpdateUserUseCaseImpl:
    """Implementation of the update user use case."""

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
        self.get_db_session = get_db_session

    async def execute(
        self, user_id: UUID, request: UpdateUserRequest, admin_user: AuthenticatedUser
    ) -> UpdateUserResponse:
        """Update a user.

        Args:
            user_id: The UUID of the user to update
            request: The update request containing the fields to update
            admin_user: The authenticated admin user performing the action

        Returns:
            Response with success message and user ID

        Raises:
            HTTPException: With appropriate status codes for validation and update errors
        """
        async with self.get_db_session() as session:
            async with session.begin():
                try:
                    # Check if user exists
                    result = await session.execute(select(User).filter_by(id=user_id))
                    user = result.scalar_one_or_none()

                    if user is None:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="User not found",
                        )

                    # Verify user belongs to admin's tenant
                    if user.tenant_id != admin_user.tenant_id:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="User not found",
                        )

                    # Update only the provided fields
                    if request.email is not None:
                        user.email = request.email

                    if request.is_active is not None:
                        user.is_active = request.is_active

                    if request.role is not None:
                        user.role = request.role

                    if request.password is not None:
                        user.hashed_password = self.password_hasher.hash(
                            request.password
                        )

                    await session.flush()

                    return UpdateUserResponse(
                        message="User updated successfully",
                        user_id=str(user.id),
                    )

                except IntegrityError:
                    await session.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User with this email already exists",
                    )
                except HTTPException:
                    # Re-raise HTTPExceptions without wrapping
                    raise
                except Exception as e:
                    await session.rollback()
                    # Log the error (in production, use proper logging)
                    print(f"Update user error: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to update user",
                    )

