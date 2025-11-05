"""Use case for deleting a user."""

from contextlib import AbstractAsyncContextManager
from typing import Callable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.schemas import AuthenticatedUser
from app.features.auth.dtos import DeleteUserResponse
from app.features.auth.models import User


class DeleteUserUseCaseImpl:
    """Implementation of the delete user use case."""

    def __init__(
        self,
        get_db_session: Callable[[], AbstractAsyncContextManager[AsyncSession]],
    ):
        """Initialize the use case with dependencies.

        Args:
            get_db_session: Function to get database session
        """
        self.get_db_session = get_db_session

    async def execute(
        self, user_id: UUID, admin_user: AuthenticatedUser
    ) -> DeleteUserResponse:
        """Delete a user and all associated data.

        Args:
            user_id: The ID of the user to delete
            admin_user: The authenticated admin user performing the action

        Returns:
            Response with success message and user ID

        Raises:
            HTTPException: With appropriate status codes for deletion errors
        """
        async with self.get_db_session() as session:
            try:
                # Fetch user
                result = await session.execute(select(User).filter_by(id=user_id))
                user = result.scalar_one_or_none()

                if not user:
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

                # Store the user ID before deletion
                user_id_str = str(user.id)

                # Delete the user (cascade will delete refresh_tokens)
                await session.delete(user)
                await session.commit()

                return DeleteUserResponse(
                    message="User deleted successfully",
                    user_id=user_id_str,
                )

            except HTTPException:
                # Re-raise HTTP exceptions (like 404)
                await session.rollback()
                raise
            except Exception as e:
                await session.rollback()
                # Log the error (in production, use proper logging)
                print(f"Delete user error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete user",
                )

