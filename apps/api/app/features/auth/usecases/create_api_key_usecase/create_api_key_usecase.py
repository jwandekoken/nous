"""Use case for creating API keys."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.authentication import get_password_hash
from app.features.auth.dtos import CreateApiKeyRequest, CreateApiKeyResponse
from app.features.auth.models import ApiKey
from app.features.auth.usecases.create_api_key_usecase.errors import (
    ApiKeyCreationFailedError,
    ApiKeyNameAlreadyExistsError,
    ValidationError,
)


class CreateApiKeyUseCaseImpl:
    """Implementation of the create API key use case."""

    def __init__(
        self,
        get_db_session,
    ):
        """Initialize the use case with dependencies.

        Args:
            get_db_session: Function to get database session
        """
        self.get_auth_db_session = get_db_session

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
            ValidationError: If API key name length is invalid
            ApiKeyNameAlreadyExistsError: If API key name already exists for this tenant
            ApiKeyCreationFailedError: If API key creation fails for unexpected reasons
        """
        # Validate input
        if len(request.name) < 3 or len(request.name) > 50:
            raise ValidationError("API key name must be between 3 and 50 characters")

        # Generate a secure key
        full_key, key_prefix = self._generate_api_key()

        # Hash the key for storage
        hashed_key = get_password_hash(full_key)

        async with self.get_auth_db_session() as session:
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

                except IntegrityError as e:
                    await session.rollback()
                    raise ApiKeyNameAlreadyExistsError() from e
                except Exception as e:
                    await session.rollback()
                    raise ApiKeyCreationFailedError() from e

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
