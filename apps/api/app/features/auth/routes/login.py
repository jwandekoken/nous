"""Login route handler."""

from typing import Any, Protocol

from fastapi import APIRouter, Depends

from app.core.authentication import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.db.postgres.auth_session import get_auth_db_session
from app.features.auth.dtos.auth_dto import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
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


async def get_login_use_case():
    """Dependency injection for the login use case."""
    return LoginUseCaseImpl(
        password_verifier=PasswordVerifierImpl(),
        token_creator=TokenCreatorImpl(),
        refresh_token_creator=RefreshTokenCreatorImpl(),
        get_db_session=get_auth_db_session,
    )


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


async def get_refresh_token_use_case():
    """Dependency injection for the refresh token use case."""
    return RefreshTokenUseCaseImpl(
        token_creator=TokenCreatorImpl(),
        refresh_token_creator=RefreshTokenCreatorImpl(),
        refresh_token_verifier=RefreshTokenVerifierImpl(),
        get_db_session=get_auth_db_session,
    )


router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login_for_access_token(
    login_data: LoginRequest,
    use_case: LoginUseCase = Depends(get_login_use_case),
) -> LoginResponse:
    """Authenticate user and return JWT access token."""
    return await use_case.execute(login_data.email, login_data.password)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(
    refresh_data: RefreshTokenRequest,
    use_case: RefreshTokenUseCase = Depends(get_refresh_token_use_case),
) -> RefreshTokenResponse:
    """Refresh access token using a valid refresh token."""
    return await use_case.execute(refresh_data.refresh_token)
