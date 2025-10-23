## Analysis of the Current Gaps

1.  **No Role Management:** The `User` model (`apps/api/app/features/auth/models.py`) has no concept of roles. Every user is equal.
2.  **Open Tenant Creation:** The `POST /api/v1/auth/create_tenant` endpoint (defined in `apps/api/app/features/auth/routes/tenants.py`) is public. As you noted, **anyone can call this endpoint**, create a new tenant, and become its first user. This is the biggest security gap.
3.  **No User Management:** There is no endpoint for an existing tenant to create _new_ users. The only way a user is created is via the public `signup_tenant` use case.
4.  **Open API Key Creation:** Any authenticated user (even a basic one) can create API keys for their tenant via `POST /api/v1/auth/api-keys`.

---

## Suggested Architecture: Implement RBAC

I suggest implementing a simple, powerful RBAC system. Here’s how, step-by-step.

### Step 1: Define Your Roles

First, let's define the roles you need. An `Enum` is perfect for this.

- **`SUPER_ADMIN`**: A system-level administrator. This is the _only_ role that can create new tenants. They do not belong to a specific tenant (or, you can assign them to a special "admin" tenant).
- **`TENANT_ADMIN`**: A tenant-level administrator. This is the _first user_ created during tenant signup. They can invite/create new users and manage API keys _for their own tenant_.
- **`TENANT_USER`**: A regular user within a tenant. They can read/write to the tenant's graph but cannot manage users or API keys.

### Step 2: Update Your `User` Model

Modify `apps/api/app/features/auth/models.py` to include the role.

```python
# In apps/api/app/features/auth/models.py
import enum
import uuid
from datetime import datetime

# Import Enum from sqlalchemy
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Enum as SAEnum, # <-- Add this import
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass

# --- Add this Enum ---
class UserRole(enum.Enum):
    """Defines the roles a user can have."""
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_USER = "tenant_user"

class Tenant(Base):
    # ... (no changes needed here)
    pass

class User(Base):
    """User model for authentication."""
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # --- Make tenant_id nullable ---
    # SUPER_ADMINs are not tied to a single tenant
    tenant_id: Mapped[uuid.UUID | None] = mapped_column( # <-- Make nullable
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=True # <-- Make nullable
    )

    # --- Add the role column ---
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), nullable=False, default=UserRole.TENANT_USER
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # ... (rest of the fields)

    # --- Make tenant relationship optional ---
    tenant: Mapped["Tenant" | None] = relationship(back_populates="users") # <-- Make nullable

class ApiKey(Base):
    # ... (no changes needed here)
    pass
```

**Next, run Alembic to generate and apply this migration:**

```bash
# From the apps/api directory
uv run alembic revision --autogenerate -m "add_role_to_user_and_make_tenant_nullable"
uv run alembic upgrade head
```

### Step 3: Update JWT and Security Dependencies

Your JWT must include the user's role to be efficient.

1.  **Update `LoginUseCaseImpl` (`apps/api/app/features/auth/usecases/login_usecase/login_usecase.py`):**
    When creating the token, add the `role` and a _nullable_ `tenant_id`.

    ```python
    # In LoginUseCaseImpl.execute
    # ... after finding and verifying the user ...

    # Convert tenant_id to string only if it exists
    tenant_id_str = str(user.tenant_id) if user.tenant_id else None

    access_token = self.token_creator(
        data={
            "sub": str(user.id),
            "tenant_id": tenant_id_str, # <-- This can be None
            "role": user.role.value       # <-- Add this
        },
        expires_delta=access_token_expires,
    )
    ```

2.  **Update `AuthenticatedUser` model (`apps/api/app/core/security.py`):**
    This model must now reflect the new JWT payload.

    ```python
    # In apps/api/app/core/security.py
    from app.features.auth.models import UserRole # <-- Import your enum

    class AuthenticatedUser(BaseModel):
        """Authenticated user with tenant information."""
        user_id: UUID
        tenant_id: UUID | None # <-- Make nullable
        role: UserRole        # <-- Add this
    ```

3.  **Update `get_current_user` dependency (`apps/api/app/core/security.py`):**
    Extract and validate the new claims.

    ```python
    # In apps/api/app/core/security.py
    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> AuthenticatedUser:
        """Get current user from JWT token with tenant information."""
        token = credentials.credentials
        payload = verify_token(token)

        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id") # This can be None
        role_str = payload.get("role")

        if user_id is None or role_str is None: # tenant_id can be None, but role cannot
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing required user or role information",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            return AuthenticatedUser(
                user_id=UUID(str(user_id)),
                tenant_id=UUID(str(tenant_id)) if tenant_id else None,
                role=UserRole(role_str) # <-- Validate and cast role
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user, tenant, or role format in token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    ```

### Step 4: Create Authorization Dependencies

Now, create reusable dependencies that check for specific roles. You can create a new file `apps/api/app/core/authorization.py` for this.

```python
# In a new file: apps/api/app/core/authorization.py
from typing import Callable
from fastapi import Depends, HTTPException, status

from app.core.security import AuthenticatedUser, get_current_user
from app.features.auth.models import UserRole

# A dependency factory
def require_roles(allowed_roles: list[UserRole]) -> Callable[..., AuthenticatedUser]:
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
```

---

## Applying the New Architecture

Now you can lock down your existing endpoints and create new, secure ones.

### Scenario 1: "Not everyone can create a tenant"

**Solution:** Protect your `create_tenant` endpoint so **only `SUPER_ADMIN`s can use it.**

1.  **Modify `apps/api/app/features/auth/routes/tenants.py`:**

    ```python
    # In apps/api/app/features/auth/routes/tenants.py
    from app.core.authorization import is_super_admin # <-- Import new dependency
    from app.core.security import AuthenticatedUser # Import this too

    # ... (other imports)

    @router.post("/create_tenant", response_model=SignupResponse)
    async def create_tenant(
        request: SignupRequest,
        use_case: SignupTenantUseCase = Depends(get_signup_tenant_use_case),
        # --- Add this protection ---
        admin_user: AuthenticatedUser = Depends(is_super_admin),
    ) -> SignupResponse:
        # ... (rest of the function)
    ```

2.  **Update `SignupTenantUseCaseImpl`:**
    The _first user_ created for a new tenant should be a **`TENANT_ADMIN`**.

    ```python
    # In apps/api/app/features/auth/usecases/signup_tenant_usecase/signup_tenant_usecase.py
    from app.features.auth.models import Tenant, User, UserRole # <-- Import UserRole

    # ...
    # In SignupTenantUseCaseImpl.execute
    # ...
                    # Create user
                    user = User(
                        email=request.email,
                        hashed_password=hashed_password,
                        tenant_id=tenant.id,
                        role=UserRole.TENANT_ADMIN  # <-- Set role to TENANT_ADMIN
                    )
                    session.add(user)
    # ...
    ```

3.  **The "First Admin" Problem:**
    You now have a chicken-and-egg problem: how do you create the _first `SUPER_ADMIN`_?
    **Solution:** Create a simple admin CLI script.

    - Create a file `scripts/create_super_admin.py`.
    - This script (which you run _once_ manually) will connect to the DB and insert the first `SUPER_ADMIN` user. This user will have `role = UserRole.SUPER_ADMIN` and `tenant_id = None`.

### Scenario 2: "Not everyone can create a new user"

**Solution:** Create a _new_ endpoint for `TENANT_ADMIN`s to invite users to _their own_ tenant.

1.  **Create a new endpoint** (e.g., in `apps/api/app/features/auth/routes/users.py` and add it to `auth/router.py`).

    ```python
    # In a new file, e.g., apps/api/app/features/auth/routes/users.py
    from fastapi import APIRouter, Depends, HTTPException
    from pydantic import BaseModel
    from app.core.authorization import is_tenant_admin
    from app.core.security import AuthenticatedUser
    from app.features.auth.models import User, UserRole
    # ... other imports for DB session, password hashing ...

    router = APIRouter()

    class CreateUserRequest(BaseModel):
        email: str
        password: str
        role: UserRole = UserRole.TENANT_USER # Default to TENANT_USER

    @router.post("/users", response_model=...) # Define a UserResponse DTO
    async def create_tenant_user(
        request: CreateUserRequest,
        admin_user: AuthenticatedUser = Depends(is_tenant_admin),
    ):
        """
        Allows a TENANT_ADMIN to create a new user within their own tenant.
        """
        if admin_user.tenant_id is None:
             # This should never happen if they are a TENANT_ADMIN, but good to check
            raise HTTPException(status_code=400, detail="Admin has no tenant")

        # You can also add logic to prevent a TENANT_ADMIN from creating another TENANT_ADMIN
        if request.role == UserRole.TENANT_ADMIN:
            raise HTTPException(status_code=403, detail="Cannot create another admin")

        # ... (Logic to create the user) ...

        hashed_password = pwd_context.hash(request.password)
        new_user = User(
            email=request.email,
            hashed_password=hashed_password,
            tenant_id=admin_user.tenant_id, # <-- Assign to admin's tenant
            role=request.role
        )

        # ... (Add to session, commit, handle IntegrityError, return response) ...
    ```

### Scenario 3: API Key Management

**Solution:** Protect the API key management endpoints so only `TENANT_ADMIN`s can create or delete them.

1.  **Modify `apps/api/app/features/auth/routes/api_keys.py`:**

    ```python
    # In apps/api/app/features/auth/routes/api_keys.py
    from app.core.authorization import is_tenant_admin # <-- Import
    from app.core.security import AuthenticatedUser
    # ...

    @router.post("/api-keys", response_model=CreateApiKeyResponse)
    async def create_api_key(
        request: CreateApiKeyRequest,
        # --- Use is_tenant_admin dependency ---
        current_user: AuthenticatedUser = Depends(is_tenant_admin),
        use_case: CreateApiKeyUseCase = Depends(get_create_api_key_use_case),
    ) -> CreateApiKeyResponse:
        # The use case already uses current_user.tenant_id, which is perfect
        return await use_case.execute(request, current_user.tenant_id)

    @router.get("/api-keys", response_model=ListApiKeysResponse)
    async def list_api_keys(
        # --- Use is_tenant_admin dependency ---
        current_user: AuthenticatedUser = Depends(is_tenant_admin),
        use_case: ListApiKeysUseCase = Depends(get_list_api_keys_use_case),
    ) -> ListApiKeysResponse:
        return await use_case.execute(current_user.tenant_id)

    @router.delete("/api-keys/{api_key_id}")
    async def delete_api_key(
        api_key_id: str,
        # --- Use is_tenant_admin dependency ---
        current_user: AuthenticatedUser = Depends(is_tenant_admin),
        use_case: DeleteApiKeyUseCase = Depends(get_delete_api_key_use_case),
    ) -> dict[str, str]:
        return await use_case.execute(api_key_id, current_user.tenant_id)
    ```
