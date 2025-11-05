"""Users data transfer objects."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.schemas import UserRole


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


class UpdateUserRequest(BaseModel):
    """Request model for updating a user."""

    email: str | None = None
    is_active: bool | None = None
    role: UserRole | None = None
    password: str | None = None


class UpdateUserResponse(BaseModel):
    """Response model for successful user update."""

    message: str
    user_id: str


class DeleteUserResponse(BaseModel):
    """Response model for successful user deletion."""

    message: str
    user_id: str


class ListUsersRequest(BaseModel):
    """Request model for listing users with pagination and filtering."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    search: str | None = None
    sort_by: str = Field(default="created_at", pattern="^(email|created_at)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class UserSummary(BaseModel):
    """Summary information about a user."""

    id: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime


class ListUsersResponse(BaseModel):
    """Response model for listing users."""

    users: list[UserSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class GetUserResponse(BaseModel):
    """Response model for getting a single user."""

    id: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    tenant_id: str
