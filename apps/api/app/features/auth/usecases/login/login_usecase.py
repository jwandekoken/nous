"""Use case for user login and token generation."""

from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Protocol

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.auth.dtos import LoginResponse
from app.features.auth.models import RefreshToken, User


class PasswordVerifier(Protocol):
    """Protocol for password verification operations."""

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        ...


class TokenCreator(Protocol):
    """Protocol for JWT token creation operations."""

    def __call__(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """Create an access token."""
        ...


class RefreshTokenCreator(Protocol):
    """Protocol for refresh token creation operations."""

    def create(self) -> str:
        """Create a refresh token."""
        ...

    def hash(self, token: str) -> str:
        """Hash a refresh token."""
        ...


class LoginUseCaseImpl:
    """Implementation of the login use case."""

    def __init__(
        self,
        password_verifier: PasswordVerifier,
        token_creator: TokenCreator,
        refresh_token_creator: RefreshTokenCreator,
        get_db_session: Callable[[], AbstractAsyncContextManager[AsyncSession]],
    ):
        """Initialize the use case with dependencies.

        Args:
            password_verifier: Service for verifying passwords
            token_creator: Service for creating access tokens
            refresh_token_creator: Service for creating refresh tokens
            get_db_session: Function to get database session
        """
        self.password_verifier = password_verifier
        self.token_creator = token_creator
        self.refresh_token_creator = refresh_token_creator
        self.get_db_session = get_db_session

    async def execute(self, email: str, password: str) -> LoginResponse:
        """Authenticate user and return JWT access token.

        Args:
            email: User's email address
            password: User's password

        Returns:
            Response with access token

        Raises:
            HTTPException: With appropriate status codes for authentication errors
        """
        async with self.get_db_session() as session:
            # Find user by email
            result = await session.execute(select(User).where(User.email == email))
            user: User | None = result.scalar_one_or_none()

            if not user or not self.password_verifier.verify(
                password, user.hashed_password
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.now(UTC):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is temporarily locked due to failed login attempts",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check if user is active
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is disabled",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Reset failed login attempts and update user
            user.failed_login_attempts = 0
            user.locked_until = None

            # Create access token with tenant info
            access_token_expires = timedelta(minutes=30)  # 30 minutes

            # Convert tenant_id to string only if it exists
            tenant_id_str = str(user.tenant_id) if user.tenant_id else None

            access_token = self.token_creator(
                data={
                    "sub": str(user.id),
                    "tenant_id": tenant_id_str,  # <-- This can be None
                    "role": user.role.value,  # <-- Add this
                },
                expires_delta=access_token_expires,
            )

            # Create and store refresh token
            settings = get_settings()
            refresh_token = self.refresh_token_creator.create()
            refresh_token_hash = self.refresh_token_creator.hash(refresh_token)
            refresh_token_expires = datetime.now(UTC) + timedelta(
                days=settings.refresh_token_expire_days
            )

            db_refresh_token = RefreshToken(
                token_hash=refresh_token_hash,
                user_id=user.id,
                expires_at=refresh_token_expires,
                revoked=False,
            )
            session.add(db_refresh_token)
            await session.commit()

            return LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=int(access_token_expires.total_seconds()),
            )
