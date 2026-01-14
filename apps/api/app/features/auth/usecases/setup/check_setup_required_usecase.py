"""Use case for checking if setup is required."""

from contextlib import AbstractAsyncContextManager
from typing import Callable

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.schemas import UserRole
from app.features.auth.dtos import SetupRequiredResponse
from app.features.auth.models import User


class CheckSetupRequiredUseCaseImpl:
    """Implementation of the check setup required use case."""

    def __init__(
        self,
        get_db_session: Callable[[], AbstractAsyncContextManager[AsyncSession]],
    ):
        """Initialize the use case with dependencies.

        Args:
            get_db_session: Function to get database session
        """
        self.get_db_session = get_db_session

    async def execute(self) -> SetupRequiredResponse:
        """Check if the application requires initial setup (no super admin exists).

        Returns:
            Response indicating if setup is required
        """
        async with self.get_db_session() as session:
            query = (
                select(func.count())
                .select_from(User)
                .where(User.role == UserRole.SUPER_ADMIN)
            )
            result = await session.execute(query)
            count = result.scalar_one()

            return SetupRequiredResponse(setup_required=count == 0)
