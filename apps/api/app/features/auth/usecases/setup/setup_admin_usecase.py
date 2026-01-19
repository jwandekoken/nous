"""Use case for setting up the first super admin."""

from contextlib import AbstractAsyncContextManager
from typing import Callable, Protocol
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import UserRole
from app.features.auth.dtos import SetupAdminRequest, SetupAdminResponse
from app.features.auth.models import User

# All fixtures are now provided by tests/conftest.py


class PasswordHasher(Protocol):
    """Protocol for password hashing operations."""

    def hash(self, secret: str | bytes, **kwargs) -> str:
        """Hash a password or secret."""
        ...


class SetupAdminUseCaseImpl:
    """Implementation of the setup admin use case."""

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

    async def execute(self, request: SetupAdminRequest) -> SetupAdminResponse:
        """Create the first super admin user. Only allowed if no super admin exists.

        Args:
            request: The setup request containing admin details

        Returns:
            Response with success message and email

        Raises:
            HTTPException: With appropriate status codes for validation and creation errors
        """
        async with self.get_db_session() as session:
            async with session.begin():
                # Check if super admin already exists
                query = (
                    select(func.count())
                    .select_from(User)
                    .where(User.role == UserRole.SUPER_ADMIN)
                )
                result = await session.execute(query)
                count = result.scalar_one()

                if count > 0:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Setup has already been completed.",
                    )

                # Check if email already exists
                email_check = await session.execute(
                    select(User).where(User.email == request.email)
                )
                if email_check.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User with this email already exists.",
                    )

                # Create super admin
                hashed_password = self.password_hasher.hash(request.password)
                super_admin = User(
                    id=uuid4(),
                    email=request.email,
                    hashed_password=hashed_password,
                    role=UserRole.SUPER_ADMIN,
                    is_active=True,
                    tenant_id=None,
                )
                session.add(super_admin)
                await session.flush()

                return SetupAdminResponse(
                    message="Super admin created successfully.",
                    email=super_admin.email,
                )
