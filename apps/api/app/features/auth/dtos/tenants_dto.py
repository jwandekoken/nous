"""Tenants data transfer objects."""

from datetime import datetime

from pydantic import BaseModel, Field


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
