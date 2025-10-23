from collections.abc import Awaitable
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.core.authentication import AuthenticatedUser, get_current_user
from app.features.auth.models import UserRole


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
