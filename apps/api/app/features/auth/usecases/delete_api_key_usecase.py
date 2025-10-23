"""Use case for deleting API keys."""

from uuid import UUID

from app.features.auth.models import ApiKey


class DeleteApiKeyUseCaseImpl:
    """Implementation of the delete API key use case."""

    def __init__(self, get_db_session):
        """Initialize the use case with dependencies.

        Args:
            get_db_session: Function to get database session
        """
        self.get_db_session = get_db_session

    async def execute(self, api_key_id: str, tenant_id: UUID) -> dict[str, str]:
        """Delete an API key.

        Args:
            api_key_id: The ID of the API key to delete
            tenant_id: The tenant ID for authorization

        Returns:
            Success message

        Raises:
            ValueError: If API key not found or access denied
        """
        try:
            uuid_obj = UUID(api_key_id)
        except ValueError as e:
            raise ValueError("Invalid API key ID format") from e

        async with self.get_db_session() as session:
            async with session.begin():
                api_key = await session.get(ApiKey, uuid_obj)

                if not api_key:
                    raise ValueError("API key not found")

                # Ensure the API key belongs to the current tenant
                if api_key.tenant_id != tenant_id:
                    raise ValueError("Access denied")

                session.delete(api_key)

        return {"message": "API key deleted successfully"}
