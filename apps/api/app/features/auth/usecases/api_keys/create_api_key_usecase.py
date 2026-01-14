"""Use case for creating API keys."""

import secrets
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import get_password_hash
from app.features.auth.dtos import CreateApiKeyRequest, CreateApiKeyResponse
from app.features.auth.models import ApiKey


class CreateApiKeyUseCaseImpl:
    """Implementation of the create API key use case."""

    def __init__(
        self,
        get_db_session: Callable[[], AbstractAsyncContextManager[AsyncSession]],
    ):
        """Initialize the use case with dependencies.

        Args:
            get_db_session: Function to get database session
        """
        self.get_db_session = get_db_session

    async def execute(
        self, request: CreateApiKeyRequest, tenant_id: UUID
    ) -> CreateApiKeyResponse:
        """Create a new API key for programmatic access.

        Args:
            request: The API key creation request
            tenant_id: The tenant ID creating the key

        Returns:
            Response with the created API key details

        Raises:
            HTTPException: With appropriate status codes for validation and creation errors
        """
        # Validate input
        if len(request.name) < 3 or len(request.name) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key name must be between 3 and 50 characters",
            )

        # Generate a secure key
        full_key, key_prefix = self._generate_api_key()

        # Hash the key for storage
        hashed_key = get_password_hash(full_key)

        async with self.get_db_session() as session:
            async with session.begin():
                try:
                    # Create API key record
                    api_key_obj = ApiKey(
                        name=request.name,
                        key_prefix=key_prefix,
                        hashed_key=hashed_key,
                        tenant_id=tenant_id,
                        expires_at=datetime.now(UTC)
                        + timedelta(days=365),  # 1 year expiry
                    )
                    session.add(api_key_obj)
                    await session.flush()

                    return CreateApiKeyResponse(
                        message="API key created successfully",
                        api_key=full_key,  # Return the plaintext key once
                        key_prefix=key_prefix,
                        expires_at=api_key_obj.expires_at.isoformat()
                        if api_key_obj.expires_at
                        else None,
                    )

                except IntegrityError:
                    await session.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="API key name already exists for this tenant",
                    )
                except Exception:
                    await session.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create API key",
                    )

    def _generate_api_key(self) -> tuple[str, str]:
        """Generate a secure API key with prefix for identification.

        Returns:
            Tuple of (full_key, prefix)
        """
        # Generate a short prefix for easy identification (10 chars)
        prefix = secrets.token_hex(5)

        # Generate the main key (43 chars when urlsafe base64 encoded)
        key = secrets.token_urlsafe(32)

        # Combine: e.g., "a1b2c3d4e5.f8jK9mNp2qRs5tUv7wX..."
        full_key = f"{prefix}.{key}"

        return full_key, prefix
