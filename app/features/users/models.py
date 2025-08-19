"""User database models using SQLModel."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    """Base user model with common fields."""

    email: str = Field(index=True, unique=True, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    """User model for database table."""

    __tablename__: str = "users"

    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(min_length=8)


class UserUpdate(SQLModel):
    """Schema for updating user information."""

    email: str | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = Field(default=None)


class UserRead(UserBase):
    """Schema for reading user data (public view)."""

    id: int
    created_at: datetime
    updated_at: datetime


class UserReadWithPassword(UserRead):
    """Schema for reading user data including password (internal use)."""

    hashed_password: str
