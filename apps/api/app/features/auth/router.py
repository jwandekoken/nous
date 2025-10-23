"""Authentication and authorization API routes."""

from typing import Any, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import (
    AuthenticatedUser,
    create_access_token,
    get_current_user,
    pwd_context,
    verify_password,
)
from app.db.postgres.auth_session import get_db_session
from app.db.postgres.graph_connection import get_db_pool
from app.features.auth.dtos import (
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    ListApiKeysResponse,
    LoginResponse,
    SignupRequest,
    SignupResponse,
)
from app.features.auth.usecases import (
    CreateApiKeyUseCaseImpl,
    DeleteApiKeyUseCaseImpl,
    ListApiKeysUseCaseImpl,
    LoginUseCaseImpl,
    SignupTenantUseCaseImpl,
)


class PasswordHasherImpl:
    """Wrapper for password hashing to match protocol."""

    def hash(self, secret: str | bytes, **kwargs) -> str:
        """Hash a password or secret."""
        return pwd_context.hash(secret, **kwargs)


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


class SignupTenantUseCase(Protocol):
    """Protocol for the signup tenant use case."""

    async def execute(self, request: SignupRequest) -> SignupResponse:
        """Create a new tenant with user and graph."""
        ...


class LoginUseCase(Protocol):
    """Protocol for the login use case."""

    async def execute(self, email: str, password: str) -> LoginResponse:
        """Authenticate user and return token."""
        ...


class CreateApiKeyUseCase(Protocol):
    """Protocol for the create API key use case."""

    async def execute(
        self, request: CreateApiKeyRequest, tenant_id: UUID
    ) -> CreateApiKeyResponse:
        """Create a new API key."""
        ...


class ListApiKeysUseCase(Protocol):
    """Protocol for the list API keys use case."""

    async def execute(self, tenant_id: UUID) -> ListApiKeysResponse:
        """List API keys for a tenant."""
        ...


class DeleteApiKeyUseCase(Protocol):
    """Protocol for the delete API key use case."""

    async def execute(self, api_key_id: str, tenant_id: UUID) -> dict[str, str]:
        """Delete an API key."""
        ...


router = APIRouter(prefix="/auth", tags=["auth"])


# Dependency injection functions
async def get_signup_tenant_use_case() -> SignupTenantUseCase:
    """Dependency injection for the signup tenant use case."""
    return SignupTenantUseCaseImpl(
        password_hasher=PasswordHasherImpl(),
        get_db_session=get_db_session,
        get_db_pool=get_db_pool,
    )


async def get_login_use_case() -> LoginUseCase:
    """Dependency injection for the login use case."""
    return LoginUseCaseImpl(
        password_verifier=PasswordVerifierImpl(),
        token_creator=TokenCreatorImpl(),
        get_db_session=get_db_session,
    )


async def get_create_api_key_use_case() -> CreateApiKeyUseCase:
    """Dependency injection for the create API key use case."""
    return CreateApiKeyUseCaseImpl(
        password_hasher=PasswordHasherImpl(),
        get_db_session=get_db_session,
    )


async def get_list_api_keys_use_case() -> ListApiKeysUseCase:
    """Dependency injection for the list API keys use case."""
    return ListApiKeysUseCaseImpl(get_db_session=get_db_session)


async def get_delete_api_key_use_case() -> DeleteApiKeyUseCase:
    """Dependency injection for the delete API key use case."""
    return DeleteApiKeyUseCaseImpl(get_db_session=get_db_session)


@router.post("/signup", response_model=SignupResponse)
async def signup_tenant(
    request: SignupRequest,
    use_case: SignupTenantUseCase = Depends(get_signup_tenant_use_case),
) -> SignupResponse:
    """Create a new tenant with an initial user and AGE graph.

    This endpoint creates:
    1. A new tenant record
    2. An initial user for the tenant
    3. A dedicated Apache AGE graph for the tenant
    """
    try:
        return await use_case.execute(request)
    except ValueError as e:
        if "Tenant name must be between 3 and 50 characters" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        elif "Tenant name can only contain" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        elif "Password must be at least 8 characters" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        elif "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )


@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    use_case: LoginUseCase = Depends(get_login_use_case),
) -> LoginResponse:
    """Authenticate user and return JWT access token."""
    try:
        return await use_case.execute(form_data.username, form_data.password)
    except ValueError as e:
        if "Incorrect email or password" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif "Account is temporarily locked" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif "Account is disabled" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )


@router.post("/api-keys", response_model=CreateApiKeyResponse)
async def create_api_key(
    request: CreateApiKeyRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: CreateApiKeyUseCase = Depends(get_create_api_key_use_case),
) -> CreateApiKeyResponse:
    """Create a new API key for programmatic access."""
    try:
        return await use_case.execute(request, current_user.tenant_id)
    except ValueError as e:
        if "API key name must be between 3 and 50 characters" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        elif "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )


@router.get("/api-keys", response_model=ListApiKeysResponse)
async def list_api_keys(
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: ListApiKeysUseCase = Depends(get_list_api_keys_use_case),
) -> ListApiKeysResponse:
    """List all API keys for the current tenant."""
    return await use_case.execute(current_user.tenant_id)


@router.delete("/api-keys/{api_key_id}")
async def delete_api_key(
    api_key_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: DeleteApiKeyUseCase = Depends(get_delete_api_key_use_case),
) -> dict[str, str]:
    """Delete an API key."""
    try:
        return await use_case.execute(api_key_id, current_user.tenant_id)
    except ValueError as e:
        if "Invalid API key ID format" in str(e):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        elif "API key not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "Access denied" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )
