"""FastAPI dependencies for tenant isolation and authentication."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy import and_, or_, select

from app.core.authentication import AuthenticatedUser, get_current_user, pwd_context
from app.db.postgres.auth_session import get_db_session
from app.features.auth.models import ApiKey, Tenant


class TenantInfo(BaseModel):
    """Tenant information including graph name."""

    tenant_id: UUID
    graph_name: str


# API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_tenant_from_api_key(
    key: str | None = Depends(api_key_header),
) -> TenantInfo | None:
    """Get tenant info from API key authentication.

    Returns None if no API key provided or if invalid.
    """
    if not key:
        return None

    # Parse the API key (format: prefix.key)
    if "." not in key:
        return None

    prefix, key_part = key.split(".", 1)
    if not prefix or not key_part:
        return None

    # Hash the full key for comparison
    hashed_key = pwd_context.hash(key)

    async with get_db_session() as session:
        # Find API key by prefix and hashed key
        result = await session.execute(
            select(ApiKey).where(
                and_(
                    ApiKey.key_prefix == prefix,
                    ApiKey.hashed_key == hashed_key,
                    or_(
                        ApiKey.expires_at.is_(None),
                        ApiKey.expires_at > datetime.now(UTC),
                    ),
                )
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        # Get the associated tenant
        tenant = await session.get(Tenant, api_key.tenant_id)
        if not tenant:
            return None

        # Update last_used_at
        api_key.last_used_at = datetime.now(UTC)
        await session.commit()

        return TenantInfo(tenant_id=tenant.id, graph_name=tenant.age_graph_name)


async def get_tenant_from_jwt(
    user: AuthenticatedUser = Depends(get_current_user),
) -> TenantInfo | None:
    """Get tenant info from JWT authentication.

    Returns None if user authentication fails.
    """
    if not user:
        return None

    async with get_db_session() as session:
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
