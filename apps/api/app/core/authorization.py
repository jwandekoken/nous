from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy import and_, or_, select

from app.core.authentication import (
    AuthenticatedUser,
    get_current_user,
    get_current_user_from_cookie,
    pwd_context,
)
from app.db.postgres.auth_session import get_auth_db_session
from app.features.auth.models import ApiKey, Tenant, UserRole


# A dependency factory
def require_roles(
    allowed_roles: list[UserRole],
) -> Callable[..., Awaitable[AuthenticatedUser]]:
    """
    Factory for creating a dependency that checks if a user has one of
    the allowed roles.
    """

    async def role_checker(
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        """
        The actual dependency that checks the user's role.
        """
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker


# --- Create your specific role dependencies ---
is_super_admin = require_roles([UserRole.SUPER_ADMIN])
is_tenant_admin = require_roles([UserRole.TENANT_ADMIN])
is_admin = require_roles([UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN])
is_any_tenant_user = require_roles([UserRole.TENANT_ADMIN, UserRole.TENANT_USER])


# --- Tenant Info and Authentication Dependencies ---
class TenantInfo(BaseModel):
    """Tenant information including graph name."""

    tenant_id: UUID
    graph_name: str


# API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_tenant_from_api_key(
    key: str | None = Depends(api_key_header),
) -> TenantInfo | None:
    """Get tenant info from API key authentication."""
    if not key or "." not in key:
        return None

    prefix, _ = key.split(".", 1)

    async with get_auth_db_session() as session:
        result = await session.execute(
            select(ApiKey).where(
                and_(
                    ApiKey.key_prefix == prefix,
                    or_(
                        ApiKey.expires_at.is_(None),
                        ApiKey.expires_at > datetime.now(UTC),
                    ),
                )
            )
        )
        api_keys = result.scalars().all()

        found_key: ApiKey | None = None
        for api_key_record in api_keys:
            if pwd_context.verify(key, api_key_record.hashed_key):
                found_key = api_key_record
                break

        if not found_key:
            return None

        tenant = await session.get(Tenant, found_key.tenant_id)
        if not tenant:
            return None

        found_key.last_used_at = datetime.now(UTC)
        await session.commit()

        return TenantInfo(tenant_id=tenant.id, graph_name=tenant.age_graph_name)


async def get_tenant_from_jwt(
    user: AuthenticatedUser = Depends(get_current_user_from_cookie),
) -> TenantInfo | None:
    """Get tenant info from JWT authentication (from cookie)."""
    if not user or not user.tenant_id:
        return None

    async with get_auth_db_session() as session:
        tenant = await session.get(Tenant, user.tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found for authenticated user",
            )
        return TenantInfo(tenant_id=user.tenant_id, graph_name=tenant.age_graph_name)


async def get_tenant_info(
    jwt_tenant: TenantInfo | None = Depends(get_tenant_from_jwt),
    api_key_tenant: TenantInfo | None = Depends(get_tenant_from_api_key),
) -> TenantInfo:
    """Master dependency that resolves tenant info from either JWT or API key.

    Prioritizes JWT over API key authentication.
    """
    if jwt_tenant:
        return jwt_tenant

    if api_key_tenant:
        return api_key_tenant

    # Neither authentication method provided or valid
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
