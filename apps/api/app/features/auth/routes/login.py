"""Login route handler."""

from typing import Any, Protocol

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from app.core.authentication import (
    create_access_token,
    create_refresh_token,
    get_current_user_from_cookie,
    hash_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.core.schemas import AuthenticatedUser
from app.core.settings import get_settings
from app.db.postgres.auth_session import get_auth_db_session
from app.features.auth.dtos.auth_dto import (
    LoginRequest,
    LoginResponse,
    RefreshTokenResponse,
)
from app.features.auth.models import RefreshToken, User
from app.features.auth.usecases.login_usecase import LoginUseCaseImpl
from app.features.auth.usecases.refresh_token_usecase import RefreshTokenUseCaseImpl


class PasswordVerifierImpl:
    """Wrapper for password verification to match protocol."""

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return verify_password(plain_password, hashed_password)


class TokenCreatorImpl:
    """Wrapper for token creation to match protocol."""

    def __call__(self, data: dict[str, Any], expires_delta=None) -> str:
        """Create an access token."""
        return create_access_token(data, expires_delta)


class RefreshTokenCreatorImpl:
    """Wrapper for refresh token creation to match protocol."""

    def create(self) -> str:
        """Create a refresh token."""
        return create_refresh_token()

    def hash(self, token: str) -> str:
        """Hash a refresh token."""
        return hash_refresh_token(token)


class RefreshTokenVerifierImpl:
    """Wrapper for refresh token verification to match protocol."""

    def verify(self, plain_token: str, hashed_token: str) -> bool:
        """Verify a refresh token against its hash."""
        return verify_refresh_token(plain_token, hashed_token)


class LoginUseCase(Protocol):
    """Protocol for the login use case."""

    async def execute(self, email: str, password: str) -> LoginResponse:
        """Authenticate user and return token."""
        ...


class RefreshTokenUseCase(Protocol):
    """Protocol for the refresh token use case."""

    async def execute(self, refresh_token: str) -> RefreshTokenResponse:
        """Refresh access token using refresh token."""
        ...


async def get_login_use_case() -> LoginUseCase:
    """Dependency injection for the login use case."""
    return LoginUseCaseImpl(
        password_verifier=PasswordVerifierImpl(),
        token_creator=TokenCreatorImpl(),
        refresh_token_creator=RefreshTokenCreatorImpl(),
        get_db_session=get_auth_db_session,
    )


async def get_refresh_token_use_case() -> RefreshTokenUseCase:
    """Dependency injection for the refresh token use case."""
    return RefreshTokenUseCaseImpl(
        token_creator=TokenCreatorImpl(),
        refresh_token_creator=RefreshTokenCreatorImpl(),
        refresh_token_verifier=RefreshTokenVerifierImpl(),
        get_db_session=get_auth_db_session,
    )


router = APIRouter()


@router.post("/login")
async def login_for_access_token(
    response: Response,
    login_data: LoginRequest,
    use_case: LoginUseCase = Depends(get_login_use_case),
) -> dict[str, str]:
    """Authenticate user and set tokens in HTTP-only cookies."""
    result = await use_case.execute(login_data.email, login_data.password)

    # Get settings for environment-specific cookie configuration
    settings = get_settings()
    is_production = not settings.debug

    # Set access token cookie
    response.set_cookie(
        key="access_token",
        value=result.access_token,
        httponly=True,  # Not accessible to JavaScript
        secure=is_production,  # Only HTTPS in production
        samesite="lax",  # CSRF protection
        max_age=result.expires_in,  # 30 minutes
        path="/",  # Available site-wide
    )

    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/api/v1/auth",  # Only sent to auth endpoints
    )

    return {"message": "Login successful", "token_type": "bearer"}


@router.post("/refresh")
async def refresh_access_token(
    response: Response,
    refresh_token: str | None = Cookie(None),
    use_case: RefreshTokenUseCase = Depends(get_refresh_token_use_case),
) -> dict[str, str]:
    """Refresh access token using refresh token from cookie."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use case returns new tokens (already implements rotation)
    result = await use_case.execute(refresh_token)

    settings = get_settings()
    is_production = not settings.debug

    # Set NEW access token cookie
    response.set_cookie(
        key="access_token",
        value=result.access_token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=result.expires_in,
        path="/",
    )

    # Set NEW refresh token cookie (rotated)
    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/api/v1/auth",
    )

    return {"message": "Token refreshed successfully", "token_type": "bearer"}


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(None),
) -> dict[str, str]:
    """Logout user and clear authentication cookies."""

    # Optional: Revoke refresh token in database
    if refresh_token:
        async with get_auth_db_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(RefreshToken).where(RefreshToken.revoked.is_(False))
            )
            db_tokens = list(result.scalars().all())

            # Find and revoke the matching token
            for token in db_tokens:
                if verify_refresh_token(refresh_token, token.token_hash):
                    token.revoked = True
                    await session.commit()
                    break

    # Clear both cookies
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")

    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user_info(
    current_user: AuthenticatedUser = Depends(get_current_user_from_cookie),
) -> dict[str, str | None]:
    """Get current authenticated user information."""
    async with get_auth_db_session() as session:
        user = await session.get(User, current_user.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        }
