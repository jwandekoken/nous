"""Use case for deleting API keys."""

from contextlib import AbstractAsyncContextManager
from typing import Callable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import ApiKey


class DeleteApiKeyUseCaseImpl:
    """Implementation of the delete API key use case."""

    def __init__(
        self, get_db_session: Callable[[], AbstractAsyncContextManager[AsyncSession]]
    ):
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
            HTTPException: With appropriate status codes for validation and access errors
        """
        try:
            uuid_obj = UUID(api_key_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid API key ID format",
            )

        async with self.get_db_session() as session:
            async with session.begin():
                api_key = await session.get(ApiKey, uuid_obj)

                if not api_key:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="API key not found",
                    )

                # Ensure the API key belongs to the current tenant
                if api_key.tenant_id != tenant_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
                    )

                await session.delete(api_key)

        return {"message": "API key deleted successfully"}
