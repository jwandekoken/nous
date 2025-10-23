"""Use case for listing API keys."""

from uuid import UUID

from sqlalchemy import select

from app.features.auth.dtos import ApiKeyInfo, ListApiKeysResponse
from app.features.auth.models import ApiKey


class ListApiKeysUseCaseImpl:
    """Implementation of the list API keys use case."""

    def __init__(self, get_db_session):
        """Initialize the use case with dependencies.

        Args:
            get_db_session: Function to get database session
        """
        self.get_db_session = get_db_session

    async def execute(self, tenant_id: UUID) -> ListApiKeysResponse:
        """List all API keys for a tenant.

        Args:
            tenant_id: The tenant ID to list keys for

        Returns:
            Response with list of API keys
        """
        async with self.get_db_session() as session:
            result = await session.execute(
                select(ApiKey).where(ApiKey.tenant_id == tenant_id)
            )
            api_keys = result.scalars().all()

            api_key_infos = [
                ApiKeyInfo(
                    id=str(api_key.id),
                    name=api_key.name,
                    key_prefix=api_key.key_prefix,
                    created_at=api_key.created_at,
                    expires_at=api_key.expires_at,
                    last_used_at=api_key.last_used_at,
                )
                for api_key in api_keys
            ]

            return ListApiKeysResponse(api_keys=api_key_infos)
