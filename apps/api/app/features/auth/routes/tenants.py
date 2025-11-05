"""Tenant route handlers."""

from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.authentication import pwd_context
from app.core.authorization import is_super_admin
from app.core.schemas import AuthenticatedUser
from app.db.postgres.auth_session import get_auth_db_session
from app.db.postgres.graph_connection import get_graph_db_pool
from app.features.auth.dtos import (
    CreateTenantRequest,
    CreateTenantResponse,
    DeleteTenantResponse,
    ListTenantsRequest,
    ListTenantsResponse,
    UpdateTenantRequest,
    UpdateTenantResponse,
)
from app.features.auth.usecases.tenants.delete_tenant_usecase import (
    DeleteTenantUseCaseImpl,
)
from app.features.auth.usecases.tenants.list_tenants_usecase import (
    ListTenantsUseCaseImpl,
)
from app.features.auth.usecases.tenants.signup_tenant_usecase import (
    SignupTenantUseCaseImpl,
)
from app.features.auth.usecases.tenants.update_tenant_usecase import (
    UpdateTenantUseCaseImpl,
)


class SignupTenantUseCase(Protocol):
    """Protocol for the signup tenant use case."""

    async def execute(self, request: CreateTenantRequest) -> CreateTenantResponse:
        """Create a new tenant with user and graph."""
        ...


class UpdateTenantUseCase(Protocol):
    """Protocol for the update tenant use case."""

    async def execute(
        self, tenant_id: UUID, request: UpdateTenantRequest
    ) -> UpdateTenantResponse:
        """Update a tenant's name."""
        ...


class DeleteTenantUseCase(Protocol):
    """Protocol for the delete tenant use case."""

    async def execute(self, tenant_id: UUID) -> DeleteTenantResponse:
        """Delete a tenant and its associated data."""
        ...


class ListTenantsUseCase(Protocol):
    """Protocol for the list tenants use case."""

    async def execute(self, request: ListTenantsRequest) -> ListTenantsResponse:
        """List tenants with pagination and filtering."""
        ...


class PasswordHasherImpl:
    """Wrapper for password hashing to match protocol."""

    def hash(self, secret: str | bytes, **kwargs) -> str:
        """Hash a password or secret."""
        return pwd_context.hash(secret, **kwargs)


async def get_signup_tenant_use_case() -> SignupTenantUseCase:
    """Dependency injection for the signup tenant use case."""
    return SignupTenantUseCaseImpl(
        password_hasher=PasswordHasherImpl(),
        get_db_session=get_auth_db_session,
        get_db_pool=get_graph_db_pool,
    )


async def get_update_tenant_use_case() -> UpdateTenantUseCase:
    """Dependency injection for the update tenant use case."""
    return UpdateTenantUseCaseImpl(
        get_db_session=get_auth_db_session,
    )


async def get_delete_tenant_use_case() -> DeleteTenantUseCase:
    """Dependency injection for the delete tenant use case."""
    return DeleteTenantUseCaseImpl(
        get_db_session=get_auth_db_session,
        get_db_pool=get_graph_db_pool,
    )


async def get_list_tenants_use_case() -> ListTenantsUseCase:
    """Dependency injection for the list tenants use case."""
    return ListTenantsUseCaseImpl(
        get_db_session=get_auth_db_session,
    )


router = APIRouter()


@router.post("/tenants", response_model=CreateTenantResponse)
async def create_tenant(
    request: CreateTenantRequest,
    use_case: SignupTenantUseCase = Depends(get_signup_tenant_use_case),
    _: AuthenticatedUser = Depends(is_super_admin),
) -> CreateTenantResponse:
    """Create a new tenant with an initial user and AGE graph.

    This endpoint creates:
    1. A new tenant record
    2. An initial user for the tenant
    3. A dedicated Apache AGE graph for the tenant
    """
    return await use_case.execute(request)


@router.patch("/tenants/{tenant_id}", response_model=UpdateTenantResponse)
async def update_tenant(
    tenant_id: UUID,
    request: UpdateTenantRequest,
    use_case: UpdateTenantUseCase = Depends(get_update_tenant_use_case),
    _: AuthenticatedUser = Depends(is_super_admin),
) -> UpdateTenantResponse:
    """Update a tenant's name.

    Only super admins can update tenant information.
    Currently only the tenant name can be updated.
    """
    return await use_case.execute(tenant_id, request)


@router.delete("/tenants/{tenant_id}", response_model=DeleteTenantResponse)
async def delete_tenant(
    tenant_id: UUID,
    use_case: DeleteTenantUseCase = Depends(get_delete_tenant_use_case),
    _: AuthenticatedUser = Depends(is_super_admin),
) -> DeleteTenantResponse:
    """Delete a tenant and all associated data.

    This will delete:
    1. The tenant record
    2. All users associated with the tenant
    3. All API keys associated with the tenant
    4. The tenant's Apache AGE graph

    Only super admins can delete tenants.
    """
    return await use_case.execute(tenant_id)


@router.get("/tenants", response_model=ListTenantsResponse)
async def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = None,
    sort_by: str = Query("created_at", pattern="^(name|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    use_case: ListTenantsUseCase = Depends(get_list_tenants_use_case),
    _: AuthenticatedUser = Depends(is_super_admin),
) -> ListTenantsResponse:
    """List all tenants with pagination and filtering.

    This endpoint allows super admins to:
    - Browse tenants with pagination
    - Search tenants by name (case-insensitive)
    - Sort by name or creation date
    - Control page size (max 100)

    Only super admins can list tenants.
    """
    request = ListTenantsRequest(
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await use_case.execute(request)
