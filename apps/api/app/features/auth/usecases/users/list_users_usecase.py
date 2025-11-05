"""Use case for listing users with pagination and filtering."""

from contextlib import AbstractAsyncContextManager
from typing import Any, Callable, Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import AuthenticatedUser
from app.features.auth.dtos import (
    ListUsersRequest,
    ListUsersResponse,
    UserSummary,
)


class ListUsersUseCase(Protocol):
    """Protocol for the list users use case."""

    async def execute(
        self, request: ListUsersRequest, admin_user: AuthenticatedUser
    ) -> ListUsersResponse:
        """List users with pagination and filtering."""
        ...


class ListUsersUseCaseImpl:
    """Implementation of the list users use case."""

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
        self, request: ListUsersRequest, admin_user: AuthenticatedUser
    ) -> ListUsersResponse:
        """List users with pagination and filtering.

        Args:
            request: The list users request containing pagination and filter parameters
            admin_user: The authenticated admin user performing the action

        Returns:
            Response with paginated user list and metadata
        """
        async with self.get_db_session() as session:
            # Build ORDER BY clause dynamically
            sort_field = request.sort_by
            sort_order = request.sort_order.upper()
            order_clause = f"{sort_field} {sort_order}"

            # Build WHERE clause - always filter by tenant_id
            where_clauses = ["u.tenant_id = :tenant_id"]
            params: dict[str, Any] = {"tenant_id": admin_user.tenant_id}

            # Add search filter if provided
            if request.search:
                search_pattern = f"%{request.search}%"
                where_clauses.append("u.email ILIKE :search")
                params["search"] = search_pattern

            where_clause = "WHERE " + " AND ".join(where_clauses)

            # Main query
            main_query = f"""
                SELECT
                    u.id,
                    u.email,
                    u.role,
                    u.is_active,
                    u.created_at
                FROM users u
                {where_clause}
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
                SELECT COUNT(*) FROM users u
                {where_clause}
            """

            # Remove pagination params for count query
            count_params = {
                k: v for k, v in params.items() if k not in ["page_size", "offset"]
            }
            count_result = await session.execute(text(count_query), count_params)
            total = count_result.scalar() or 0

            # Convert to response models
            from app.core.schemas import UserRole

            users = [
                UserSummary(
                    id=str(row.id),
                    email=row.email,
                    role=UserRole[row.role],  # Access enum by name (TENANT_ADMIN -> UserRole.TENANT_ADMIN)
                    is_active=row.is_active,
                    created_at=row.created_at,
                )
                for row in rows
            ]

            total_pages = (total + request.page_size - 1) // request.page_size

            return ListUsersResponse(
                users=users,
                total=total,
                page=request.page,
                page_size=request.page_size,
                total_pages=total_pages,
            )

