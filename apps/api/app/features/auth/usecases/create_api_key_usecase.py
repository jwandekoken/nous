"""Use case for creating API keys."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.features.auth.dtos import CreateApiKeyRequest, CreateApiKeyResponse
from app.features.auth.models import ApiKey


class PasswordHasher(Protocol):
    """Protocol for password hashing operations."""

    def hash(self, secret: str | bytes, **kwargs) -> str:
        """Hash a password or API key."""
        ...


class CreateApiKeyUseCaseImpl:
    """Implementation of the create API key use case."""

    def __init__(
        self,
        password_hasher: PasswordHasher,
        get_db_session,
    ):
        """Initialize the use case with dependencies.

        Args:
            password_hasher: Service for hashing API keys
            get_db_session: Function to get database session
        """
        self.password_hasher = password_hasher
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
            ValueError: If validation fails or creation fails
        """
        # Validate input
        if len(request.name) < 3 or len(request.name) > 50:
            raise ValueError("API key name must be between 3 and 50 characters")

        async with self.get_db_session() as session:
            async with session.begin():
                try:
                    # Generate API key
                    full_key, prefix = self._generate_api_key()
                    hashed_key = self.password_hasher.hash(full_key)

                    # Create API key record
                    api_key = ApiKey(
                        name=request.name,
                        key_prefix=prefix,
                        hashed_key=hashed_key,
                        tenant_id=tenant_id,
                        expires_at=datetime.now(UTC)
                        + timedelta(days=365),  # 1 year expiry
                    )
                    session.add(api_key)
                    await session.commit()

                    return CreateApiKeyResponse(
                        message="API key created successfully",
                        api_key=full_key,  # Return the plaintext key once
                        key_prefix=prefix,
                        expires_at=api_key.expires_at.isoformat()
                        if api_key.expires_at
                        else None,
                    )

                except IntegrityError as e:
                    await session.rollback()
                    raise ValueError(
                        "API key name already exists for this tenant"
                    ) from e
                except Exception as e:
                    await session.rollback()
                    raise ValueError("Failed to create API key") from e

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
