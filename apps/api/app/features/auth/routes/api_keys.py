"""API keys route handlers."""

from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import AuthenticatedUser, get_current_user, pwd_context
from app.db.postgres.auth_session import get_auth_db_session
from app.features.auth.dtos import (
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    ListApiKeysResponse,
)
from app.features.auth.usecases import (
    CreateApiKeyUseCaseImpl,
    DeleteApiKeyUseCaseImpl,
    ListApiKeysUseCaseImpl,
)


class PasswordHasherImpl:
    """Wrapper for password hashing to match protocol."""

    def hash(self, secret: str | bytes, **kwargs) -> str:
        """Hash a password or secret."""
        return pwd_context.hash(secret, **kwargs)


async def get_create_api_key_use_case():
    """Dependency injection for the create API key use case."""
    return CreateApiKeyUseCaseImpl(
        password_hasher=PasswordHasherImpl(),
        get_db_session=get_auth_db_session,
    )


async def get_list_api_keys_use_case():
    """Dependency injection for the list API keys use case."""
    return ListApiKeysUseCaseImpl(get_db_session=get_auth_db_session)


async def get_delete_api_key_use_case():
    """Dependency injection for the delete API key use case."""
    return DeleteApiKeyUseCaseImpl(get_db_session=get_auth_db_session)


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


router = APIRouter()


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
