"""Use case for deleting a tenant."""

from collections.abc import Awaitable
from contextlib import AbstractAsyncContextManager
from typing import Callable
from uuid import UUID

import asyncpg
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.auth.dtos import DeleteTenantResponse
from app.features.auth.models import Tenant


class DeleteTenantUseCaseImpl:
    """Implementation of the delete tenant use case."""

    def __init__(
        self,
        get_db_session: Callable[[], AbstractAsyncContextManager[AsyncSession]],
        get_db_pool: Callable[[], Awaitable[asyncpg.Pool]],
    ):
        """Initialize the use case with dependencies.

        Args:
            get_db_session: Function to get database session
            get_db_pool: Function to get graph database pool
        """
        self.get_db_session = get_db_session
        self.get_graph_db_pool = get_db_pool

    async def execute(self, tenant_id: UUID) -> DeleteTenantResponse:
        """Delete a tenant, including its AGE graph and all associated users.

        Args:
            tenant_id: The ID of the tenant to delete

        Returns:
            Response with success message and tenant ID

        Raises:
            HTTPException: With appropriate status codes for deletion errors
        """
        async with self.get_db_session() as session:
            async with session.begin():
                try:
                    # Fetch tenant
                    result = await session.execute(
                        select(Tenant).filter_by(id=tenant_id)
                    )
                    tenant = result.scalar_one_or_none()

                    if not tenant:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Tenant not found",
                        )

                    # Store the graph name before deletion
                    graph_name = tenant.age_graph_name
                    tenant_id_str = str(tenant.id)

                    # Delete the AGE graph first
                    pool = await self.get_graph_db_pool()
                    async with pool.acquire() as conn:
                        await conn.execute("LOAD 'age';")
                        await conn.execute(
                            "SET search_path = ag_catalog, '$user', public;"
                        )
                        # The 'true' parameter cascades the deletion
                        await conn.execute("SELECT drop_graph($1, true)", graph_name)

                    # Delete the tenant (cascade will delete users and api_keys)
                    await session.delete(tenant)
                    await session.flush()

                    return DeleteTenantResponse(
                        message="Tenant deleted successfully",
                        tenant_id=tenant_id_str,
                    )

                except HTTPException:
                    # Re-raise HTTP exceptions (like 404)
                    await session.rollback()
                    raise
                except Exception as e:
                    await session.rollback()
                    # Log the error (in production, use proper logging)
                    print(f"Delete tenant error: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to delete tenant",
                    )
