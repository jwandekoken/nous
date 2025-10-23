"""Login route handler."""

from typing import Any, Protocol

from fastapi import APIRouter, Depends

from app.core.authentication import create_access_token, verify_password
from app.db.postgres.auth_session import get_auth_db_session
from app.features.auth.dtos.auth_dto import LoginRequest, LoginResponse
from app.features.auth.usecases.login_usecase import LoginUseCaseImpl


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


async def get_login_use_case():
    """Dependency injection for the login use case."""
    return LoginUseCaseImpl(
        password_verifier=PasswordVerifierImpl(),
        token_creator=TokenCreatorImpl(),
        get_db_session=get_auth_db_session,
    )


class LoginUseCase(Protocol):
    """Protocol for the login use case."""

    async def execute(self, email: str, password: str) -> LoginResponse:
        """Authenticate user and return token."""
        ...


router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login_for_access_token(
    login_data: LoginRequest,
    use_case: LoginUseCase = Depends(get_login_use_case),
) -> LoginResponse:
    """Authenticate user and return JWT access token."""
    return await use_case.execute(login_data.email, login_data.password)
