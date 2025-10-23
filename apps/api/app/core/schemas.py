import enum
import uuid

from pydantic import BaseModel


class UserRole(enum.Enum):
    """Defines the roles a user can have."""

    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_USER = "tenant_user"


class AuthenticatedUser(BaseModel):
    """Represents an authenticated user."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    role: UserRole
