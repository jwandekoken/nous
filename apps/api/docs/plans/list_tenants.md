# Plan: Implement List Tenants Endpoint

## Overview

Implement a new endpoint to list all tenants with pagination and filtering capabilities. This endpoint will be restricted to super admins only.

## Current Architecture Analysis

Based on the existing codebase structure:

### Routes Pattern (`tenants.py`)

- Uses FastAPI APIRouter
- Implements CRUD operations: create, update, delete
- Uses dependency injection for use cases
- Authorization via `is_super_admin` dependency
- Response models defined in `dtos.py`

### Use Case Pattern (`signup_tenant_usecase.py`)

- Protocol-based design with implementation classes
- Dependency injection for database sessions and external services
- Comprehensive input validation
- Proper error handling with HTTPException
- Transaction management with rollback on errors

### Testing Pattern (`test_signup_tenant_usecase_integration.py`)

- Integration tests using pytest-asyncio
- Fixtures provided by `tests/conftest.py`
- Tests both success and failure scenarios
- Database state verification
- Parametrized tests for validation

## Implementation Plan

### 1. Create DTOs (`app/features/auth/dtos.py`)

Add new request/response models:

```python
class ListTenantsRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    search: Optional[str] = None
    sort_by: Optional[str] = Field(default="created_at", pattern="^(name|created_at)$")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")

class ListTenantsResponse(BaseModel):
    tenants: List[TenantSummary]
    total: int
    page: int
    page_size: int
    total_pages: int

class TenantSummary(BaseModel):
    id: str
    name: str
    age_graph_name: str
    created_at: datetime
    user_count: int
```

### 2. Create Use Case (`app/features/auth/usecases/list_tenants_usecase.py`)

```python
class ListTenantsUseCase(Protocol):
    async def execute(self, request: ListTenantsRequest) -> ListTenantsResponse:
        ...

class ListTenantsUseCaseImpl:
    def __init__(self, get_db_session: Callable):
        self.get_db_session = get_db_session

    async def execute(self, request: ListTenantsRequest) -> ListTenantsResponse:
        # Implement pagination, filtering, and counting
        # Join with users table to get user_count
        # Apply search filter if provided
        # Sort by specified field and order
```

### 3. Add Route Handler (`app/features/auth/routes/tenants.py`)

```python
@router.get("/tenants", response_model=ListTenantsResponse)
async def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(name|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    use_case: ListTenantsUseCase = Depends(get_list_tenants_use_case),
    _: AuthenticatedUser = Depends(is_super_admin),
) -> ListTenantsResponse:
    request = ListTenantsRequest(
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await use_case.execute(request)
```

### 4. Update Route Imports (`app/features/auth/routes/tenants.py`)

- Import new DTOs
- Import new use case
- Add dependency injection function `get_list_tenants_use_case()`

### 5. Create Integration Tests (`tests/features/auth/usecases/test_list_tenants_usecase_integration.py`)

Test scenarios:

- Successful listing with default pagination
- Pagination with custom page and page_size
- Search filtering
- Sorting by different fields
- Empty result set
- Authorization (non-super-admin access denied)
- Invalid parameters validation

### 6. Update Router (`app/features/auth/router.py`)

No changes needed - tenants router already included.

## Database Query Considerations

### Primary Approach: Raw SQL Queries

Using raw SQL for optimal performance and simplicity. SQLAlchemy provides parameterized query execution with proper escaping:

```python
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

class ListTenantsUseCaseImpl:
    async def execute(self, request: ListTenantsRequest) -> ListTenantsResponse:
        async with self.get_db_session() as session:
            # Build search pattern
            search_pattern = f"%{request.search}%" if request.search else None

            # Build ORDER BY clause dynamically
            sort_field = request.sort_by
            sort_order = request.sort_order.upper()
            order_clause = f"{sort_field} {sort_order}"

            # Main query with LEFT JOIN for user count
            main_query = """
                SELECT
                    t.id,
                    t.name,
                    t.age_graph_name,
                    t.created_at,
                    COUNT(u.id) as user_count
                FROM tenants t
                LEFT JOIN users u ON t.id = u.tenant_id
                WHERE (:search IS NULL OR t.name ILIKE :search)
                GROUP BY t.id, t.name, t.age_graph_name, t.created_at
                ORDER BY {order_clause}
                LIMIT :page_size OFFSET :offset
            """.format(order_clause=order_clause)

            # Execute main query
            result = await session.execute(
                text(main_query),
                {
                    "search": search_pattern,
                    "page_size": request.page_size,
                    "offset": (request.page - 1) * request.page_size,
                }
            )
            rows = result.fetchall()

            # Count query for total records
            count_query = """
                SELECT COUNT(*) FROM tenants t
                WHERE (:search IS NULL OR t.name ILIKE :search)
            """

            count_result = await session.execute(
                text(count_query),
                {"search": search_pattern}
            )
            total = count_result.scalar()

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
```

### Benefits of Raw SQL Approach

- **Performance**: Direct SQL execution without ORM overhead
- **Clarity**: Explicit control over the exact SQL being executed
- **Optimization**: Can leverage database-specific features (ILIKE for PostgreSQL)
- **Simplicity**: Straightforward query construction and parameter binding

### Alternative: SQLAlchemy ORM Queries (if preferred later)

```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.auth.models import Tenant, User

# Using ORM with select() and joins
stmt = (
    select(
        Tenant.id,
        Tenant.name,
        Tenant.age_graph_name,
        Tenant.created_at,
        func.count(User.id).label("user_count")
    )
    .outerjoin(User, Tenant.id == User.tenant_id)
    .where(Tenant.name.ilike(f"%{request.search}%") if request.search else True)
    .group_by(Tenant.id, Tenant.name, Tenant.age_graph_name, Tenant.created_at)
    .order_by(getattr(Tenant, request.sort_by).asc() if request.sort_order == "asc" else getattr(Tenant, request.sort_by).desc())
    .limit(request.page_size)
    .offset((request.page - 1) * request.page_size)
)

result = await session.execute(stmt)
tenants_data = result.all()
```

## Security Considerations

- Endpoint restricted to super admins only
- Input validation for all query parameters
- SQL injection prevention via parameterized queries
- No sensitive data exposure (passwords, etc.)

## Performance Considerations

- Pagination to limit result sets
- Database indexes on frequently queried fields (name, created_at)
- Efficient counting with separate count query
- Connection pooling via existing session management

## Testing Strategy

- Unit tests for use case logic
- Integration tests for full request flow
- Database state verification
- Authorization testing
- Edge case testing (empty results, large datasets)

## Migration Plan

1. Implement DTOs first
2. Create use case implementation
3. Add route handler
4. Create comprehensive tests
5. Test manually via API
6. Deploy and monitor

## Open Questions

- Should we include soft-deleted tenants?
- Any additional filtering options needed (created date range, etc.)?
- Do we need caching for frequently accessed data?
- Should we add rate limiting for this endpoint?
