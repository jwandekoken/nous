"""Use case for listing tenants with pagination and filtering."""

from contextlib import AbstractAsyncContextManager
from typing import Any, Callable, Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.dtos import (
    ListTenantsRequest,
    ListTenantsResponse,
    TenantSummary,
)


class ListTenantsUseCase(Protocol):
    """Protocol for the list tenants use case."""

    async def execute(self, request: ListTenantsRequest) -> ListTenantsResponse:
        """List tenants with pagination and filtering."""
        ...


class ListTenantsUseCaseImpl:
    """Implementation of the list tenants use case."""

    def __init__(
        self,
        get_db_session: Callable[[], AbstractAsyncContextManager[AsyncSession]],
    ):
        """Initialize the use case with dependencies.

        Args:
            get_db_session: Function to get database session
        """
        self.get_db_session = get_db_session

    async def execute(self, request: ListTenantsRequest) -> ListTenantsResponse:
        """List tenants with pagination and filtering.

        Args:
            request: The list tenants request containing pagination and filter parameters

        Returns:
            Response with paginated tenant list and metadata
        """
        async with self.get_db_session() as session:
            # Build ORDER BY clause dynamically
            sort_field = request.sort_by
            sort_order = request.sort_order.upper()
            order_clause = f"{sort_field} {sort_order}"

            # Build WHERE clause conditionally
            params: dict[str, Any]
            if request.search:
                search_pattern = f"%{request.search}%"
                where_clause = "WHERE t.name ILIKE :search"
                params = {"search": search_pattern}
            else:
                where_clause = ""
                params = {}

            # Main query with LEFT JOIN for user count
            main_query = f"""
                SELECT
                    t.id,
                    t.name,
                    t.age_graph_name,
                    t.created_at,
                    COUNT(u.id) as user_count
                FROM tenants t
                LEFT JOIN users u ON t.id = u.tenant_id
                {where_clause}
                GROUP BY t.id, t.name, t.age_graph_name, t.created_at
                ORDER BY {order_clause}
                LIMIT :page_size OFFSET :offset
            """

            # Add pagination parameters
            params["page_size"] = request.page_size
            params["offset"] = (request.page - 1) * request.page_size

            # Execute main query
            result = await session.execute(text(main_query), params)
            rows = result.fetchall()

            # Count query for total records
            count_query = f"""
                SELECT COUNT(*) FROM tenants t
                {where_clause}
            """

            # Remove pagination params for count query
            count_params = {
                k: v for k, v in params.items() if k not in ["page_size", "offset"]
            }
            count_result = await session.execute(text(count_query), count_params)
            total = count_result.scalar() or 0

            # Convert to response models
            tenants = [
                TenantSummary(
                    id=str(row.id),
                    name=row.name,
                    age_graph_name=row.age_graph_name,
                    created_at=row.created_at,
                    user_count=row.user_count,
                )
                for row in rows
            ]

            total_pages = (total + request.page_size - 1) // request.page_size

            return ListTenantsResponse(
                tenants=tenants,
                total=total,
                page=request.page,
                page_size=request.page_size,
                total_pages=total_pages,
            )
