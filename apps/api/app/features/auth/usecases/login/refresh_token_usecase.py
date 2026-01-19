"""Use case for refreshing access tokens."""

from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Protocol

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.auth.dtos import RefreshTokenResponse
from app.features.auth.models import RefreshToken, User


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


class RefreshTokenVerifier(Protocol):
    """Protocol for refresh token verification operations."""

    def verify(self, plain_token: str, hashed_token: str) -> bool:
        """Verify a refresh token against its hash."""
        ...


class RefreshTokenUseCaseImpl:
    """Implementation of the refresh token use case."""

    def __init__(
        self,
        token_creator: TokenCreator,
        refresh_token_creator: RefreshTokenCreator,
        refresh_token_verifier: RefreshTokenVerifier,
        get_db_session: Callable[[], AbstractAsyncContextManager[AsyncSession]],
    ):
        """Initialize the use case with dependencies.

        Args:
            token_creator: Service for creating access tokens
            refresh_token_creator: Service for creating refresh tokens
            refresh_token_verifier: Service for verifying refresh tokens
            get_db_session: Function to get database session
        """
        self.token_creator = token_creator
        self.refresh_token_creator = refresh_token_creator
        self.refresh_token_verifier = refresh_token_verifier
        self.get_db_session = get_db_session

    async def execute(self, refresh_token: str) -> RefreshTokenResponse:
        """Refresh access token using a valid refresh token.

        Args:
            refresh_token: The refresh token from the request

        Returns:
            Response with new access token and refresh token

        Raises:
            HTTPException: With appropriate status codes for validation errors
        """
        async with self.get_db_session() as session:
            # Find refresh token in database
            result = await session.execute(
                select(RefreshToken)
                .where(RefreshToken.revoked == False)  # noqa: E712
                .order_by(RefreshToken.created_at.desc())
            )
            db_tokens: list[RefreshToken] = list(result.scalars().all())

            # Find matching token by verifying hash
            db_refresh_token: RefreshToken | None = None
            for token in db_tokens:
                if self.refresh_token_verifier.verify(refresh_token, token.token_hash):
                    db_refresh_token = token
                    break

            if not db_refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check if token is expired
            if db_refresh_token.expires_at < datetime.now(UTC):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Get the associated user
            user_result = await session.execute(
                select(User).where(User.id == db_refresh_token.user_id)
            )
            user: User | None = user_result.scalar_one_or_none()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check if user account is locked
            if user.locked_until and user.locked_until > datetime.now(UTC):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is temporarily locked",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check if user is active
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is disabled",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Create new access token
            access_token_expires = timedelta(minutes=30)
            tenant_id_str = str(user.tenant_id) if user.tenant_id else None

            access_token = self.token_creator(
                data={
                    "sub": str(user.id),
                    "tenant_id": tenant_id_str,
                    "role": user.role.value,
                },
                expires_delta=access_token_expires,
            )

            # Create new refresh token (token rotation)
            settings = get_settings()
            new_refresh_token = self.refresh_token_creator.create()
            new_refresh_token_hash = self.refresh_token_creator.hash(new_refresh_token)
            new_refresh_token_expires = datetime.now(UTC) + timedelta(
                days=settings.refresh_token_expire_days
            )

            new_db_refresh_token = RefreshToken(
                token_hash=new_refresh_token_hash,
                user_id=user.id,
                expires_at=new_refresh_token_expires,
                revoked=False,
            )
            session.add(new_db_refresh_token)
            await session.flush()  # Flush to get the new token's ID

            # Revoke old refresh token and link to new one
            db_refresh_token.revoked = True
            db_refresh_token.replaced_by_id = new_db_refresh_token.id

            await session.commit()

            return RefreshTokenResponse(
                access_token=access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=int(access_token_expires.total_seconds()),
            )
