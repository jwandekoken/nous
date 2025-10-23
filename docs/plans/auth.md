## 1. Core Concept: Tenant-Graph Isolation

The central challenge is that each tenant needs their _own_ Apache AGE graph. Your current `AgeRepository` is hard-coded to use a single graph name from the settings.

**Our strategy will be:**

1.  **Store Tenant Metadata in SQL:** We will create standard PostgreSQL tables (outside of AGE) to store `Tenant`, `User`, and `ApiKey` information.
2.  **Link Tenant to Graph:** The `Tenant` table will have a column, `age_graph_name`, which stores the unique name of their specific graph (e.g., `graph_tenant_acme_corp`).
3.  **Dynamic Repository Injection:** We will modify `AgeRepository` to accept the `graph_name` as a constructor argument.
4.  **Auth-Powered Dependency:** We will create a new FastAPI dependency, `get_tenant_info`, that:
    - Authenticates the request (via a User's JWT _or_ an App's API Key).
    - Identifies the associated `tenant_id`.
    - Looks up the tenant's `age_graph_name` from the SQL table.
    - Injects this `graph_name` into the `AgeRepository` for that specific request.

This ensures all graph operations are automatically and securely scoped to the correct tenant's graph.

### 1.1: Error Handling & Validation Patterns

**Critical Error Scenarios to Handle:**

1. **Graph Creation Failures:** If `create_graph()` fails during signup, the entire transaction must rollback
2. **API Key Expiration:** Return 401 with clear message when API key is expired
3. **Tenant Not Found:** Return 404 when tenant doesn't exist for a valid user
4. **Database Connection Issues:** Implement retry logic with exponential backoff
5. **Validation Rules:**
   - Tenant name: unique, 3-50 chars, alphanumeric + hyphens
   - Email: valid format, unique per tenant
   - Password: minimum 8 chars, complexity requirements
   - API key name: unique per tenant, 3-50 chars

**Error Response Standards:**

```python
# Use consistent error responses
HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Tenant name already exists"
)

HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="API key has expired",
    headers={"WWW-Authenticate": "Bearer"}
)
```

**Transaction Handling with SQLAlchemy:**

```python
from app.features.auth.models import Tenant, User
from app.db.postgres.auth_session import get_db_session
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

async def signup_tenant(name: str, email: str, password: str, graph_name: str):
    async with get_db_session() as session:
        async with session.begin():
            try:
                # Create tenant
                tenant = Tenant(name=name, age_graph_name=graph_name)
                session.add(tenant)
                await session.flush()  # Get the tenant ID

                # Create user
                hashed_password = get_password_hash(password)
                user = User(
                    email=email,
                    hashed_password=hashed_password,
                    tenant_id=tenant.id
                )
                session.add(user)
                await session.flush()

                # Create AGE graph (this can fail)
                from app.db.postgres.graph_connection import get_db_pool
                pool = await get_db_pool()
                async with pool.acquire() as conn:
                    await conn.execute("SELECT create_graph($1)", graph_name)

                return {"message": "Tenant created successfully", "tenant_id": tenant.id}

            except IntegrityError:
                await session.rollback()
                raise HTTPException(400, "Tenant name or email already exists")
            except Exception as e:
                await session.rollback()
                logger.error(f"Database error during signup: {e}")
                raise HTTPException(500, "Failed to create tenant")
```

---

## 2. Plan: Backend (FastAPI)

### Step 2.0: Database Migration Setup (Alembic)

To manage the SQL schema changes in a structured and version-controlled way, we will use Alembic. This is a critical first step before creating the tables.

**1. Installation:**

First, add Alembic as a dependency to the API project using `uv`.

```bash
cd apps/api
uv add alembic
```

**2. Initialization:**

From the `apps/api` directory, run the Alembic initialization command using `uv run`.

```bash
cd apps/api
uv run alembic init migrations
```

This creates a `migrations` directory and an `alembic.ini` file.

**3. Configuration:**

- **`alembic.ini`**: Update the `sqlalchemy.url` to point to your database. It's best to read this from your application's settings.

  ```ini
  # at the top of the file
  [alembic]
  # ... other settings
  script_location = migrations

  # a little further down
  sqlalchemy.url = postgresql+asyncpg://user:password@host/dbname
  ```

- **`migrations/env.py`**: This file needs to be configured to find your database models and settings.
  - Make sure `target_metadata` is correctly set up if you are using SQLAlchemy models. Since we are writing raw SQL, this is less critical, but good practice.
  - Configure it to use your application's database connection string from `app.core.settings`.

**4. SQLAlchemy Models First (Recommended):**

Create SQLAlchemy models for type safety and better migration generation:

```python
# apps/api/app/features/auth/models.py
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Tenant(Base):
    """Tenant model representing isolated organizations."""
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    age_graph_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    """User model for authentication."""
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="users")


class ApiKey(Base):
    """API key model for programmatic access."""
    __tablename__ = "api_key"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    hashed_key: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="api_keys")

    # Constraints
    __table_args__ = (
        UniqueConstraint('name', 'tenant_id', name='unique_api_key_name_per_tenant'),
    )
```

**5. Creating the Migration:**

After defining models, generate the migration:

```bash
uv run alembic revision --autogenerate -m "create_auth_tables"
```

This creates a migration file that Alembic generates based on your models. Review and adjust the generated migration as needed.

**5. Applying the Migration:**

To apply this to your database, run:

```bash
uv run alembic upgrade head
```

This makes your schema management repeatable and safe. All future schema changes should be done by creating new Alembic revisions.

### Step 2.1: New "Auth" Feature

Create a new feature directory: `apps/api/app/features/auth`.

**1. `features/auth/models.py`:**
Create Pydantic models for these new tables (e.g., `Tenant`, `User`, `ApiKey`).

**2. `features/auth/router.py`:**
This router will handle user login.

- **`POST /auth/token` (Login):**

  - This endpoint will take a username (email) and password.
  - It will query the new `user` table.
  - It will use `verify_password` from `core.security`.
  - If valid, it will call `create_access_token` from `core.security`.
  - **Crucially:** The JWT payload **must** include the `tenant_id`:
    ```python
    data = {"sub": str(user.id), "tenant_id": str(user.tenant_id)}
    access_token = create_access_token(data=data)
    return {"access_token": access_token, "token_type": "bearer"}
    ```

- **`POST /auth/signup` (Tenant/User Creation):**

  - This endpoint will be responsible for creating a new `Tenant` and their first `User`.
  - It must also **create the new Apache AGE graph** for that tenant.
  - **Logic:**
    1.  Receive `name`, `email`, `password`.
    2.  Generate a unique `age_graph_name` (e.g., `f"nous_graph_{uuid.uuid4().hex}"`).
    3.  **In a single transaction:**
        - `INSERT` into the `tenant` table (with the new `age_graph_name`).
        - `INSERT` into the `user` table (linking to the new tenant).
        - Execute `SELECT create_graph($1);` using the new `age_graph_name`.
    4.  Return a success message or log the user in.

- **`POST /auth/api-keys` (API Key Creation):**

  - This endpoint will generate secure API keys for programmatic access.
  - **Key Generation Strategy:**

    ```python
    import secrets

    def generate_api_key():
        """Generate a secure API key with prefix for identification."""
        # Generate a short prefix for easy identification (10 chars)
        prefix = secrets.token_hex(5)

        # Generate the main key (43 chars when urlsafe base64 encoded)
        key = secrets.token_urlsafe(32)

        # Combine: e.g., "a1b2c3d4e5.f8jK9mNp2qRs5tUv7wX..."
        full_key = f"{prefix}.{key}"

        return full_key

    # Example output: "a1b2c3d4e5.f8jK9mNp2qRs5tUv7wX..."
    ```

  - **Storage:** Only store the `prefix` and `hashed_key` in database.
  - **Return:** Return the full plaintext key **once** - user must copy it immediately.
  - **Validation:** API key names must be unique per tenant.

### Step 2.2: Update Core Security & Dependencies

**1. `core/security.py`:**

- Add required imports:

  ```python
  from uuid import UUID
  from pydantic import BaseModel
  ```

- Create a Pydantic model for the authenticated user payload:

  ```python
  class AuthenticatedUser(BaseModel):
      user_id: UUID
      tenant_id: UUID
  ```

- Update `get_current_user` to return typed `AuthenticatedUser`:

  ```python
  async def get_current_user(
      credentials: HTTPAuthorizationCredentials = Depends(security),
  ) -> AuthenticatedUser:
      """Get current user from JWT token with tenant information."""
      token = credentials.credentials
      payload = verify_token(token)

      user_id = payload.get("sub")
      tenant_id = payload.get("tenant_id")

      if user_id is None or tenant_id is None:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Token missing required user or tenant information",
              headers={"WWW-Authenticate": "Bearer"},
          )

      try:
          return AuthenticatedUser(
              user_id=UUID(user_id),
              tenant_id=UUID(tenant_id)
          )
      except ValueError:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Invalid user or tenant ID format",
              headers={"WWW-Authenticate": "Bearer"},
          )
  ```

**2. New Tenant Dependency (The Magic):**
Create a new file `app/core/dependencies.py` (or similar).

```python
from datetime import datetime, UTC
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy import and_, or_, select, delete

from app.core.security import get_current_user, AuthenticatedUser, pwd_context
from app.db.postgres.auth_session import get_db_session
from app.features.auth.models import ApiKey, Tenant

# 1. Define models for tenant info
class TenantInfo(BaseModel):
    tenant_id: UUID
    graph_name: str

# 2. Define API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# 3. Dependency to get TenantInfo from API Key
async def get_tenant_from_api_key(
    key: str | None = Depends(api_key_header)
) -> TenantInfo | None:
    if not key:
        return None

    # Use the same passlib context from core.security for consistency
    from app.core.security import pwd_context
    hashed_key = pwd_context.hash(key)

    # Query API key and tenant using SQLAlchemy ORM
    from app.features.auth.models import ApiKey, Tenant
    from sqlalchemy import and_, or_

    async with get_db_session() as session:
        api_key = await session.execute(
            select(ApiKey).where(
                and_(
                    ApiKey.hashed_key == hashed_key,
                    or_(
                        ApiKey.expires_at.is_(None),
                        ApiKey.expires_at > datetime.now(UTC)
                    )
                )
            )
        ).scalar_one_or_none()

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

# 4. Dependency to get TenantInfo from JWT
async def get_tenant_from_jwt(
    user: AuthenticatedUser = Depends(get_current_user)
) -> TenantInfo | None:
    if not user:
        return None

    # Query the tenant using SQLAlchemy ORM
    from app.features.auth.models import Tenant

    async with get_db_session() as session:
        tenant = await session.get(Tenant, user.tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found for user")

        return TenantInfo(tenant_id=user.tenant_id, graph_name=tenant.age_graph_name)

# 5. Master Tenant Dependency
async def get_tenant_info(
    jwt_tenant: TenantInfo | None = Depends(get_tenant_from_jwt),
    api_key_tenant: TenantInfo | None = Depends(get_tenant_from_api_key),
) -> TenantInfo:
    """
    Master dependency that resolves tenant info from either
    a user's JWT or an application's API key.
    """
    if jwt_tenant:
        return jwt_tenant

    if api_key_tenant:
        return api_key_tenant

    # If neither is provided or valid
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
```

### Step 2.3: Update Repository and Use Cases

**1. `features/graph/repositories/age_repository.py`:**

- Modify the `__init__` method.
- **Remove** `self.graph_name = get_settings().age_graph_name`.
- The new `__init__` should be:
  ```python
  def __init__(self, pool: asyncpg.Pool, graph_name: str):
      """Initialize the repository with a database connection pool and a dynamic graph name."""
      self.pool = pool
      self.graph_name = graph_name
      if not graph_name:
           raise ValueError("graph_name must be provided")
  ```
- The `_execute_cypher` method already uses `self.graph_name`, so all repository methods will _automatically_ work with the tenant-specific graph.

**2. `features/graph/router.py`:**

- Update the use case dependencies to inject the `TenantInfo`.

- Import your new master dependency: `from app.core.dependencies import get_tenant_info, TenantInfo`.

- Update `get_assimilate_knowledge_use_case` and `get_get_entity_use_case`:

  ```python
  async def get_assimilate_knowledge_use_case(
      tenant_info: TenantInfo = Depends(get_tenant_info), # <-- ADD THIS
  ) -> AssimilateKnowledgeUseCase:
      """Dependency injection for the assimilate knowledge use case."""

      # Get database pool and pass the tenant's graph name to the repository
      pool = await get_db_pool()
      repo = AgeRepository(pool, graph_name=tenant_info.graph_name)

      return AssimilateKnowledgeUseCaseImpl(
          repository=repo, fact_extractor=_fact_extractor
  )

  async def get_get_entity_use_case(
      tenant_info: TenantInfo = Depends(get_tenant_info), # <-- ADD THIS
  ) -> GetEntityUseCase:
      """Dependency injection for the get entity use case."""

      # Get database pool and pass the tenant's graph name to the repository
      pool = await get_db_pool()
      repo = AgeRepository(pool, graph_name=tenant_info.graph_name)

      return GetEntityUseCaseImpl(repository=repo)
  ```

- Your main API endpoints (`assimilate_knowledge` and `get_entity`) require no other changes. They will automatically fail with a 401 if no valid JWT or API key is provided.

### Step 2.4: Production Security & Rate Limiting

**1. Rate Limiting Setup:**

Add `slowapi` for rate limiting protection:

```bash
uv add slowapi
```

**Configuration:**

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

# Add to FastAPI app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

**Rate Limits:**

```python
# Auth endpoints - strict limits
@router.post("/auth/token")
@limiter.limit("5/minute")
async def login(...):
    # Login logic

@router.post("/auth/signup")
@limiter.limit("3/hour")
async def signup(...):
    # Signup logic

# API key creation - moderate limits
@router.post("/auth/api-keys")
@limiter.limit("10/hour")
async def create_api_key(...):
    # API key creation logic
```

**2. Security Headers Middleware:**

Create security headers middleware for production:

```python
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content Security Policy (adjust for your needs)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )

        return response

# Add to FastAPI app
app.add_middleware(SecurityHeadersMiddleware)
```

**3. Account Lockout Protection:**

Implement failed login attempt tracking:

```python
# Add to user table: failed_login_attempts (integer), locked_until (timestamptz)

from app.features.auth.models import User
from app.db.postgres.auth_session import get_db_session
from sqlalchemy import update

async def check_account_lockout(email: str) -> bool:
    """Check if account is temporarily locked due to failed attempts."""
    async with get_db_session() as session:
        user = await session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if not user:
            return False

        if user.locked_until and user.locked_until > datetime.now(UTC):
            return True

        return False

async def record_failed_login(email: str):
    """Record a failed login attempt and potentially lock account."""
    async with get_db_session() as session:
        user = await session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if not user:
            return

        user.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.now(UTC) + timedelta(minutes=15)

        await session.commit()

async def record_successful_login(email: str):
    """Reset failed login attempts on successful login."""
    async with get_db_session() as session:
        await session.execute(
            update(User).where(User.email == email).values(
                failed_login_attempts=0,
                locked_until=None
            )
        )
        await session.commit()
```

---

## 3. Plan: Front-End (Vue.js)

### Step 3.1: Update Login View

- `features/login/views/LoginView.vue`:

  - The existing `handleLogin` is a mock. It needs to call the new `/api/v1/auth/token` endpoint.
  - Create `features/auth/api/authApi.ts` to encapsulate this `POST` request.
  - On successful login, use `TokenManager.setTokens()` to store both access and refresh tokens.
  - Handle login errors with proper user feedback.
  - Redirect to `/`.

  ```typescript
  // features/auth/api/authApi.ts
  import { useApiFetch } from "@/api/useApiFetch";

  export const authApi = {
    async login(email: string, password: string) {
      const { data, error } = await useApiFetch("/auth/token", {
        method: "POST",
        body: { username: email, password }, // OAuth2 expects 'username'
      }).json();

      if (error.value) {
        throw new Error(error.value.detail || "Login failed");
      }

      return data.value;
    },

    async refreshToken(refreshToken: string) {
      const { data, error } = await useApiFetch("/auth/refresh", {
        method: "POST",
        body: { refresh_token: refreshToken },
      }).json();

      if (error.value) {
        throw new Error("Token refresh failed");
      }

      return data.value;
    },
  };
  ```

### Step 3.2: Update `useApiFetch`

- `api/useApiFetch.ts`:

  - Implement secure token storage and automatic refresh logic.

  ```typescript
  // Token management utilities
  class TokenManager {
    private static readonly ACCESS_TOKEN_KEY = "access_token";
    private static readonly REFRESH_TOKEN_KEY = "refresh_token";

    static getAccessToken(): string | null {
      return localStorage.getItem(this.ACCESS_TOKEN_KEY);
    }

    static getRefreshToken(): string | null {
      return localStorage.getItem(this.REFRESH_TOKEN_KEY);
    }

    static setTokens(accessToken: string, refreshToken?: string): void {
      localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
      if (refreshToken) {
        localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken);
      }
    }

    static clearTokens(): void {
      localStorage.removeItem(this.ACCESS_TOKEN_KEY);
      localStorage.removeItem(this.REFRESH_TOKEN_KEY);
    }

    static isTokenExpired(token: string): boolean {
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        const currentTime = Date.now() / 1000;
        return payload.exp < currentTime;
      } catch {
        return true;
      }
    }

    static async refreshAccessToken(): Promise<string | null> {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) return null;

      try {
        const response = await fetch(`${BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (response.ok) {
          const data = await response.json();
          this.setTokens(data.access_token, data.refresh_token);
          return data.access_token;
        }
      } catch (error) {
        console.error("Token refresh failed:", error);
      }

      return null;
    }
  }

  export const useApiFetch = createFetch({
    baseUrl: BASE_URL,
    options: {
      async beforeFetch({ options }) {
        let token = TokenManager.getAccessToken();

        // Check if token is expired or will expire soon (within 5 minutes)
        if (token && TokenManager.isTokenExpired(token)) {
          token = await TokenManager.refreshAccessToken();
        }

        if (token) {
          options.headers = {
            ...options.headers,
            Authorization: `Bearer ${token}`,
          };
        }
        return { options };
      },

      async onFetchError(ctx) {
        // Handle 401 errors by attempting token refresh
        if (ctx.response?.status === 401) {
          const newToken = await TokenManager.refreshAccessToken();
          if (newToken) {
            // Retry the request with new token
            ctx.options.headers = {
              ...ctx.options.headers,
              Authorization: `Bearer ${newToken}`,
            };
            return ctx.fetch(ctx.url, ctx.options);
          }
        }
        return ctx;
      },
    },
  });

  // Export token manager for use in components
  export { TokenManager };
  ```

**Security Note:** While localStorage is used here for simplicity, consider implementing **httpOnly cookies** for production:

- Set JWT as httpOnly cookie from `/auth/token` endpoint
- Use a separate refresh token endpoint that sets refresh token as httpOnly cookie
- Implement CSRF protection with SameSite cookies
- The frontend would not need to manage tokens directly

### Step 3.3: Update Route Guard & Logout

- `features/graph/routes.ts`:

  - The `isAuthenticated` function in the `beforeEnter` guard should be updated to check for the real token:
    ```typescript
    const isAuthenticated = () => {
      const token = localStorage.getItem("access_token");
      // You could also add JWT decoding here to check for expiration
      return !!token;
    };
    ```

- `components/layout/navigation/Navigation.vue`:

  - The `handleLogout` function should use `TokenManager.clearTokens()` and optionally call logout endpoint:

    ```typescript
    import { TokenManager } from "@/api/useApiFetch";

    const handleLogout = async () => {
      try {
        // Optional: Call logout endpoint to invalidate server-side session
        await useApiFetch("/auth/logout", { method: "POST" });
      } catch (error) {
        console.warn("Logout endpoint failed:", error);
      }

      // Clear all tokens
      TokenManager.clearTokens();

      // Redirect to login
      router.push("/login");
    };
    ```

### Step 3.4: (Future) Tenant Admin Page

- Create a new view for tenant administration (e.g., `/settings`).
- This page will allow a logged-in user to:
  - View their tenant info.
  - Create new API keys (calling a new `POST /api/v1/api-keys` endpoint).
  - Revoke existing API keys (calling `DELETE /api/v1/api-keys/{key_id}`).
- When creating an API key, the backend will generate the key, store its hash, and return the _plaintext key_ to the UI **once**. The UI must instruct the user to copy it immediately.

### 3.5: API Key Rotation Strategy

**Key Rotation with Overlap Periods:**

Implement a secure rotation strategy to minimize service disruption:

```python
class ApiKeyRotationService:
    """Service for managing API key rotation with overlap periods."""

    async def rotate_api_key(
        self,
        api_key_id: UUID,
        overlap_hours: int = 24,
        pool: asyncpg.Pool
    ) -> dict:
        """
        Rotate an API key with overlap period for zero-downtime rotation.

        1. Generate new key
        2. Keep old key active for overlap period
        3. Mark old key as deprecated
        4. Return both keys with expiration info
        """
        # Generate new key
        new_key_full = generate_api_key()
        new_key_prefix = new_key_full.split('.')[0]
        new_key_hash = pwd_context.hash(new_key_full)

        async with get_db_session() as session:
            async with session.begin():
                # Get current key info
                old_key = await session.get(ApiKey, api_key_id)
                if not old_key:
                    raise HTTPException(404, "API key not found")

                # Create new key (active immediately)
                new_key = ApiKey(
                    name=f"{old_key.name}_rotated",
                    key_prefix=new_key_prefix,
                    hashed_key=new_key_hash,
                    tenant_id=old_key.tenant_id,
                    expires_at=datetime.now(UTC) + timedelta(days=365)
                )
                session.add(new_key)
                await session.flush()

                # Mark old key as expiring soon (overlap period)
                old_key.expires_at = datetime.now(UTC) + timedelta(hours=overlap_hours)
                old_key.name = f"{old_key.name}_deprecated"

        return {
            "new_key": new_key_full,
            "old_key_expires_at": f"{overlap_hours} hours from now",
            "message": f"New key is active immediately. Old key remains valid for {overlap_hours} hours."
        }
```

**Deprecation Warnings:**

Add middleware to warn about deprecated keys:

```python
async def check_deprecated_key(api_key_prefix: str) -> dict | None:
    """Check if API key is deprecated and return warning info."""
    async with get_db_session() as session:
        deprecated_key = await session.execute(
            select(ApiKey).where(
                and_(
                    ApiKey.key_prefix == api_key_prefix,
                    ApiKey.name.like("%_deprecated")
                )
            )
        ).scalar_one_or_none()

        if deprecated_key and deprecated_key.expires_at:
            hours_remaining = int((deprecated_key.expires_at - datetime.now(UTC)).total_seconds() / 3600)
            if hours_remaining > 0:
                return {
                    "warning": "deprecated_key",
                    "message": f"This API key is deprecated and will expire in {hours_remaining} hours. Please rotate to the new key.",
                    "expires_at": deprecated_key.expires_at
                }
    return None
```

**Automatic Cleanup:**

Background job to remove expired keys:

```python
async def cleanup_expired_api_keys():
    """Remove API keys that have expired."""
    async with get_db_session() as session:
        await session.execute(
            delete(ApiKey).where(ApiKey.expires_at < datetime.now(UTC))
        )
        await session.commit()
```

### Step 2.5: Comprehensive Testing Strategy

**Unit Tests:**

```python
# tests/core/test_security.py
import uuid
import pytest
from app.core.security import AuthenticatedUser, verify_password, get_password_hash

class TestAuthenticatedUser:
    def test_valid_user_creation(self):
        user = AuthenticatedUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4())
        assert user.user_id is not None
        assert user.tenant_id is not None

class TestPasswordHashing:
    def test_password_hashing(self):
        password = "test_password"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)

class TestTokenValidation:
    def test_valid_token_decoding(self):
        # Test JWT token creation and validation
        pass

    def test_expired_token_rejection(self):
        # Test expired token handling
        pass
```

**Integration Tests:**

```python
# tests/features/auth/test_auth_integration.py
import uuid
import pytest
from httpx import AsyncClient
from app.main import app
from app.core.security import get_password_hash

class TestAuthIntegration:
    async def test_tenant_creation_and_login(self, client: AsyncClient):
        """Test complete tenant creation and login flow."""
        # Create tenant
        signup_data = {
            "name": "TestTenant",
            "email": "admin@testtenant.com",
            "password": "SecurePass123!"
        }
        response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == 200

        # Login with created user
        login_data = {
            "username": "admin@testtenant.com",
            "password": "SecurePass123!"
        }
        response = await client.post("/api/v1/auth/token", data=login_data)
        assert response.status_code == 200

        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

    async def test_tenant_isolation(self, client: AsyncClient):
        """Test that tenants cannot access each other's graphs."""
        # Create two tenants
        # Login as tenant A
        # Verify tenant A cannot access tenant B's data
        pass

    async def test_api_key_authentication(self, client: AsyncClient):
        """Test API key authentication flow."""
        # Create tenant and API key
        # Use API key to authenticate requests
        # Verify tenant isolation
        pass

class TestRateLimiting:
    async def test_login_rate_limiting(self, client: AsyncClient):
        """Test that login attempts are rate limited."""
        login_data = {"username": "test@example.com", "password": "wrong"}

        # Make multiple failed login attempts
        for _ in range(6):
            response = await client.post("/api/v1/auth/token", data=login_data)

        # Should be rate limited
        assert response.status_code == 429

class TestSecurityHeaders:
    async def test_security_headers_present(self, client: AsyncClient):
        """Test that security headers are present in responses."""
        response = await client.get("/health")

        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
```

**Security Tests:**

```python
# tests/features/auth/test_security.py
class TestSecurityVulnerabilities:
    async def test_no_jwt_tenant_isolation_bypass(self, client: AsyncClient):
        """Test that JWT without tenant_id is rejected."""
        # Create JWT without tenant_id
        # Verify request is rejected with 401
        pass

    async def test_api_key_prefix_collision_prevention(self):
        """Test that API key prefixes cannot collide."""
        # Attempt to create API keys with same prefix
        # Verify collision is prevented
        pass

    async def test_graph_creation_failure_rollback(self):
        """Test that failed graph creation rolls back tenant creation."""
        # Mock graph creation failure
        # Verify tenant is not created
        pass

class TestTokenSecurity:
    async def test_refresh_token_rotation(self, client: AsyncClient):
        """Test that refresh tokens are properly rotated."""
        # Login and get tokens
        # Use refresh token
        # Verify old refresh token is invalidated
        pass

    async def test_concurrent_session_handling(self, client: AsyncClient):
        """Test handling of concurrent sessions."""
        # Login multiple times
        # Use old token after new login
        # Verify old token is invalidated
        pass
```

**Frontend Tests:**

```typescript
// src/features/auth/__tests__/TokenManager.test.ts
import { TokenManager } from "@/api/useApiFetch";

describe("TokenManager", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should store and retrieve tokens", () => {
    const accessToken = "access_token_123";
    const refreshToken = "refresh_token_456";

    TokenManager.setTokens(accessToken, refreshToken);

    expect(TokenManager.getAccessToken()).toBe(accessToken);
    expect(TokenManager.getRefreshToken()).toBe(refreshToken);
  });

  it("should detect expired tokens", () => {
    const expiredToken =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

    expect(TokenManager.isTokenExpired(expiredToken)).toBe(true);
  });

  it("should clear all tokens on logout", () => {
    TokenManager.setTokens("access", "refresh");
    TokenManager.clearTokens();

    expect(TokenManager.getAccessToken()).toBeNull();
    expect(TokenManager.getRefreshToken()).toBeNull();
  });
});
```

**Load Testing Considerations:**

- Test concurrent tenant creation
- Test API key authentication under load
- Test token refresh during high traffic
- Monitor database connection pool usage

**CI/CD Integration:**

```yaml
# .github/workflows/test.yml
- name: Run Auth Tests
  run: |
    uv run pytest tests/features/auth/ -v
    uv run pytest tests/core/test_security.py -v
- name: Run Frontend Tests
  run: |
    pnpm test -- features/auth/
```
