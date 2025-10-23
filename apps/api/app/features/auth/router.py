"""Authentication and authorization API routes."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import (
    AuthenticatedUser,
    create_access_token,
    get_current_user,
    get_password_hash,
    pwd_context,
    verify_password,
)
from app.db.postgres.auth_session import get_db_session
from app.db.postgres.graph_connection import get_db_pool
from app.features.auth.models import ApiKey, Tenant, User


# Pydantic models for API requests/responses
class SignupRequest(BaseModel):
    """Request model for tenant signup."""

    name: str
    email: str
    password: str


class SignupResponse(BaseModel):
    """Response model for successful signup."""

    message: str
    tenant_id: str
    user_id: str


class LoginResponse(BaseModel):
    """Response model for successful login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CreateApiKeyRequest(BaseModel):
    """Request model for creating an API key."""

    name: str


class CreateApiKeyResponse(BaseModel):
    """Response model for successful API key creation."""

    message: str
    api_key: str
    key_prefix: str
    expires_at: str | None


class ApiKeyInfo(BaseModel):
    """Information about an API key."""

    id: str
    name: str
    key_prefix: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None


class ListApiKeysResponse(BaseModel):
    """Response model for listing API keys."""

    api_keys: list[ApiKeyInfo]


def generate_api_key() -> tuple[str, str]:
    """Generate a secure API key with prefix for identification.

    Returns:
        Tuple of (full_key, prefix)
    """
    # Generate a short prefix for easy identification (10 chars)
    prefix = secrets.token_hex(5)

    # Generate the main key (43 chars when urlsafe base64 encoded)
    key = secrets.token_urlsafe(32)

    # Combine: e.g., "a1b2c3d4e5.f8jK9mNp2qRs5tUv7wX..."
    full_key = f"{prefix}.{key}"

    return full_key, prefix


def generate_unique_graph_name() -> str:
    """Generate a unique graph name for a tenant."""
    return f"nous_graph_{uuid.uuid4().hex}"


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=SignupResponse)
async def signup_tenant(request: SignupRequest) -> SignupResponse:
    """Create a new tenant with an initial user and AGE graph.

    This endpoint creates:
    1. A new tenant record
    2. An initial user for the tenant
    3. A dedicated Apache AGE graph for the tenant
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

    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    async with get_db_session() as session:
        async with session.begin():
            try:
                # Generate unique graph name
                graph_name = generate_unique_graph_name()

                # Create tenant
                tenant = Tenant(name=request.name, age_graph_name=graph_name)
                session.add(tenant)
                await session.flush()  # Get the tenant ID

                # Hash password
                hashed_password = get_password_hash(request.password)

                # Create user
                user = User(
                    email=request.email,
                    hashed_password=hashed_password,
                    tenant_id=tenant.id,
                )
                session.add(user)
                await session.flush()

                # Create AGE graph
                pool = await get_db_pool()
                async with pool.acquire() as conn:
                    await conn.execute("LOAD 'age';")
                    await conn.execute("SET search_path = ag_catalog, '$user', public;")
                    await conn.execute("SELECT create_graph($1)", graph_name)

                return SignupResponse(
                    message="Tenant created successfully",
                    tenant_id=str(tenant.id),
                    user_id=str(user.id),
                )

            except IntegrityError:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tenant name or email already exists",
                )
            except Exception as e:
                await session.rollback()
                # Log the error (in production, use proper logging)
                print(f"Signup error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create tenant",
                )


@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> LoginResponse:
    """Authenticate user and return JWT access token."""

    async with get_db_session() as session:
        # Find user by email
        result = await session.execute(
            select(User).where(User.email == form_data.username)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is temporarily locked due to failed login attempts",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Reset failed login attempts and update user
        user.failed_login_attempts = 0
        user.locked_until = None
        await session.commit()

        # Create access token with tenant info
        access_token_expires = timedelta(minutes=30)  # 30 minutes
        access_token = create_access_token(
            data={"sub": str(user.id), "tenant_id": str(user.tenant_id)},
            expires_delta=access_token_expires,
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
        )


@router.post("/api-keys", response_model=CreateApiKeyResponse)
async def create_api_key(
    request: CreateApiKeyRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CreateApiKeyResponse:
    """Create a new API key for programmatic access."""

    # Validate input
    if len(request.name) < 3 or len(request.name) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key name must be between 3 and 50 characters",
        )

    async with get_db_session() as session:
        async with session.begin():
            try:
                # Generate API key
                full_key, prefix = generate_api_key()
                hashed_key = pwd_context.hash(full_key)

                # Create API key record
                api_key = ApiKey(
                    name=request.name,
                    key_prefix=prefix,
                    hashed_key=hashed_key,
                    tenant_id=current_user.tenant_id,
                    expires_at=datetime.now(UTC) + timedelta(days=365),  # 1 year expiry
                )
                session.add(api_key)
                await session.commit()

                return CreateApiKeyResponse(
                    message="API key created successfully",
                    api_key=full_key,  # Return the plaintext key once
                    key_prefix=prefix,
                    expires_at=api_key.expires_at.isoformat()
                    if api_key.expires_at
                    else None,
                )

            except IntegrityError:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="API key name already exists for this tenant",
                )
            except Exception:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create API key",
                )


@router.get("/api-keys", response_model=ListApiKeysResponse)
async def list_api_keys(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ListApiKeysResponse:
    """List all API keys for the current tenant."""

    async with get_db_session() as session:
        api_keys = (
            await session.execute(
                select(ApiKey).where(ApiKey.tenant_id == current_user.tenant_id)
            )
            .scalars()
            .all()
        )

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


@router.delete("/api-keys/{api_key_id}")
async def delete_api_key(
    api_key_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, str]:
    """Delete an API key."""

    try:
        uuid_obj = uuid.UUID(api_key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid API key ID format"
        )

    async with get_db_session() as session:
        async with session.begin():
            api_key = await session.get(ApiKey, uuid_obj)

            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
                )

            # Ensure the API key belongs to the current tenant
            if api_key.tenant_id != current_user.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
                )

            await session.delete(api_key)

        return {"message": "API key deleted successfully"}
