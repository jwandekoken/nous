"""Use case for user login and token generation."""

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import select

from app.features.auth.dtos import LoginResponse
from app.features.auth.models import User


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


class LoginUseCaseImpl:
    """Implementation of the login use case."""

    def __init__(
        self,
        password_verifier: PasswordVerifier,
        token_creator: TokenCreator,
        get_db_session,
    ):
        """Initialize the use case with dependencies.

        Args:
            password_verifier: Service for verifying passwords
            token_creator: Service for creating access tokens
            get_db_session: Function to get database session
        """
        self.password_verifier = password_verifier
        self.token_creator = token_creator
        self.get_auth_db_session = get_db_session

    async def execute(self, email: str, password: str) -> LoginResponse:
        """Authenticate user and return JWT access token.

        Args:
            email: User's email address
            password: User's password

        Returns:
            Response with access token

        Raises:
            ValueError: If authentication fails or account is locked/disabled
        """
        async with self.get_auth_db_session() as session:
            # Find user by email
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user or not self.password_verifier.verify(
                password, user.hashed_password
            ):
                raise ValueError("Incorrect email or password")

            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.now(UTC):
                raise ValueError(
                    "Account is temporarily locked due to failed login attempts"
                )

            # Check if user is active
            if not user.is_active:
                raise ValueError("Account is disabled")

            # Reset failed login attempts and update user
            user.failed_login_attempts = 0
            user.locked_until = None
            await session.commit()

            # Create access token with tenant info
            access_token_expires = timedelta(minutes=30)  # 30 minutes
            access_token = self.token_creator(
                data={"sub": str(user.id), "tenant_id": str(user.tenant_id)},
                expires_delta=access_token_expires,
            )

            return LoginResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=int(access_token_expires.total_seconds()),
            )
