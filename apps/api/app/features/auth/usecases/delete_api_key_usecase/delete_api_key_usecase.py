"""Use case for deleting API keys."""

from uuid import UUID

from app.features.auth.models import ApiKey
from app.features.auth.usecases.delete_api_key_usecase.errors import (
    ApiKeyAccessDeniedError,
    ApiKeyNotFoundError,
    InvalidApiKeyIdFormatError,
)


class DeleteApiKeyUseCaseImpl:
    """Implementation of the delete API key use case."""

    def __init__(self, get_db_session):
        """Initialize the use case with dependencies.

        Args:
            get_db_session: Function to get database session
        """
        self.get_auth_db_session = get_db_session

    async def execute(self, api_key_id: str, tenant_id: UUID) -> dict[str, str]:
        """Delete an API key.

        Args:
            api_key_id: The ID of the API key to delete
            tenant_id: The tenant ID for authorization

        Returns:
            Success message

        Raises:
            InvalidApiKeyIdFormatError: If API key ID format is invalid
            ApiKeyNotFoundError: If API key not found
            ApiKeyAccessDeniedError: If API key doesn't belong to the tenant
        """
        try:
            uuid_obj = UUID(api_key_id)
        except ValueError as e:
            raise InvalidApiKeyIdFormatError() from e

        async with self.get_auth_db_session() as session:
            async with session.begin():
                api_key = await session.get(ApiKey, uuid_obj)

                if not api_key:
                    raise ApiKeyNotFoundError()

                # Ensure the API key belongs to the current tenant
                if api_key.tenant_id != tenant_id:
                    raise ApiKeyAccessDeniedError()

                session.delete(api_key)

        return {"message": "API key deleted successfully"}
