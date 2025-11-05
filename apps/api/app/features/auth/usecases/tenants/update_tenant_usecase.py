"""Use case for updating a tenant's name."""

from contextlib import AbstractAsyncContextManager
from typing import Callable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.auth.dtos import UpdateTenantRequest, UpdateTenantResponse
from app.features.auth.models import Tenant


class UpdateTenantUseCaseImpl:
    """Implementation of the update tenant use case."""

    def __init__(
        self,
        get_db_session: Callable[[], AbstractAsyncContextManager[AsyncSession]],
    ):
        """Initialize the use case with dependencies.

        Args:
            get_db_session: Function to get database session
        """
        self.get_auth_db_session = get_db_session

    async def execute(
        self, tenant_id: UUID, request: UpdateTenantRequest
    ) -> UpdateTenantResponse:
        """Update a tenant's name.

        Args:
            tenant_id: The UUID of the tenant to update
            request: The update request containing the new name

        Returns:
            Response with success message and tenant ID

        Raises:
            HTTPException: With appropriate status codes for validation and update errors
        """
        # Validate input
        if len(request.name) < 3 or len(request.name) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name must be between 3 and 50 characters",
            )

        if not request.name.replace("-", "").replace("_", "").isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name can only contain alphanumeric characters, hyphens, and underscores",
            )

        async with self.get_auth_db_session() as session:
            async with session.begin():
                try:
                    # Check if tenant exists
                    result = await session.execute(
                        select(Tenant).filter_by(id=tenant_id)
                    )
                    tenant = result.scalar_one_or_none()

                    if tenant is None:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Tenant not found",
                        )

                    # Update tenant name
                    tenant.name = request.name
                    await session.flush()

                    return UpdateTenantResponse(
                        message="Tenant updated successfully",
                        tenant_id=str(tenant.id),
                    )

                except IntegrityError:
                    await session.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Tenant name already exists",
                    )
                except HTTPException:
                    # Re-raise HTTPExceptions without wrapping
                    raise
                except Exception as e:
                    await session.rollback()
                    # Log the error (in production, use proper logging)
                    print(f"Update tenant error: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to update tenant",
                    )
