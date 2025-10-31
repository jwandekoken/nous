"""Authentication and authorization data transfer objects."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.schemas import UserRole


class CreateTenantRequest(BaseModel):
    """Request model for tenant creation."""

    name: str
    email: str
    password: str


class CreateTenantResponse(BaseModel):
    """Response model for successful tenant creation."""

    message: str
    tenant_id: str
    user_id: str


class LoginRequest(BaseModel):
    """Request model for user login."""

    email: str
    password: str


class LoginResponse(BaseModel):
    """Response model for successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Request model for refreshing access token."""

    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Response model for successful token refresh."""

    access_token: str
    refresh_token: str
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


class CreateUserRequest(BaseModel):
    """Request model for creating a new user."""

    email: str
    password: str


class CreateUserResponse(BaseModel):
    """Response model for successful user creation."""

    message: str
    user_id: str
    email: str
    role: UserRole


class UpdateTenantRequest(BaseModel):
    """Request model for updating a tenant."""

    name: str


class UpdateTenantResponse(BaseModel):
    """Response model for successful tenant update."""

    message: str
    tenant_id: str


class DeleteTenantResponse(BaseModel):
    """Response model for successful tenant deletion."""

    message: str
    tenant_id: str


class ListTenantsRequest(BaseModel):
    """Request model for listing tenants with pagination and filtering."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    search: str | None = None
    sort_by: str = Field(default="created_at", pattern="^(name|created_at)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class TenantSummary(BaseModel):
    """Summary information about a tenant."""

    id: str
    name: str
    age_graph_name: str
    created_at: datetime
    user_count: int


class ListTenantsResponse(BaseModel):
    """Response model for listing tenants."""

    tenants: list[TenantSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
