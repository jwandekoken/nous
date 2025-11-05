"""Use case for getting a single user by ID."""

from contextlib import AbstractAsyncContextManager
from typing import Callable, Protocol
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.schemas import AuthenticatedUser
from app.features.auth.dtos import GetUserResponse
from app.features.auth.models import User


class GetUserUseCase(Protocol):
    """Protocol for the get user use case."""

    async def execute(
        self, user_id: UUID, admin_user: AuthenticatedUser
    ) -> GetUserResponse:
        """Get a single user by ID."""
        ...


class GetUserUseCaseImpl:
    """Implementation of the get user use case."""

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
    ) -> GetUserResponse:
        """Get a single user by ID.

        Args:
            user_id: The ID of the user to retrieve
            admin_user: The authenticated admin user performing the action

        Returns:
            Response with user details

        Raises:
            HTTPException: With appropriate status codes for validation and retrieval errors
        """
        async with self.get_db_session() as session:
            # Fetch the user
            result = await session.execute(select(User).filter_by(id=user_id))
            user = result.scalar_one_or_none()

            # Check if user exists
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

            return GetUserResponse(
                id=str(user.id),
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                tenant_id=str(user.tenant_id),
            )

