# Authentication Implementation Plan

## Overview

This document outlines the implementation plan for a secure authentication system using **HTTP-only cookies** to store JWT access tokens and refresh tokens. This approach provides the best security for a Single Page Application (SPA) by protecting tokens from XSS attacks while maintaining a seamless user experience.

## Table of Contents

1. [Authentication Approach](#authentication-approach)
2. [Current State Analysis](#current-state-analysis)
3. [Authentication Flow](#authentication-flow)
4. [Backend Implementation](#backend-implementation)
5. [Frontend Implementation](#frontend-implementation)
6. [Security Considerations](#security-considerations)
7. [Implementation Steps](#implementation-steps)
8. [Testing Strategy](#testing-strategy)

---

## Authentication Approach

### HTTP-only Cookies Strategy

**Why HTTP-only Cookies?**

- ✅ **XSS Protection**: Tokens are inaccessible to JavaScript, preventing theft via XSS attacks
- ✅ **Automatic Management**: Browsers automatically send cookies with requests
- ✅ **Persistent Sessions**: Survives page refreshes without manual storage
- ✅ **CSRF Protection**: Combined with `SameSite` attribute provides strong CSRF defense

**Token Strategy:**

- **Access Token**: Short-lived (30 minutes), stored in HTTP-only cookie
- **Refresh Token**: Long-lived (30 days), stored in HTTP-only cookie with rotation
- **Token Rotation**: Each refresh generates a new refresh token and revokes the old one

---

## Current State Analysis

### Backend Current State

**Existing Infrastructure** ✅

```
apps/api/app/
├── core/
│   ├── authentication.py    # JWT creation, password hashing, token verification
│   ├── authorization.py     # Role-based access control, tenant resolution
│   └── schemas.py           # AuthenticatedUser, UserRole schemas
├── features/auth/
│   ├── routes/
│   │   └── login.py        # Login and refresh endpoints (returns JSON)
│   ├── usecases/
│   │   ├── login_usecase.py           # Login business logic
│   │   └── refresh_token_usecase.py   # Token refresh with rotation ✅
│   ├── dtos/
│   │   └── auth_dto.py     # LoginRequest, LoginResponse, etc.
│   └── models.py           # User, Tenant, RefreshToken, ApiKey models
└── main.py                 # CORS configured with allow_credentials=True ✅
```

**What Works:**

- ✅ JWT creation and verification
- ✅ Refresh token rotation (already implemented!)
- ✅ Password hashing with Argon2
- ✅ CORS with `allow_credentials=True`
- ✅ Role-based authorization
- ✅ API Key authentication (alternative auth method)

**What Needs to Change:**

- ❌ Login endpoint returns tokens in JSON body (needs to set cookies)
- ❌ Refresh endpoint accepts token from request body (needs to read from cookie)
- ❌ `get_current_user` reads from `Authorization` header (needs cookie option)
- ❌ No logout endpoint

### Frontend Current State

**Existing Infrastructure** ✅

```
apps/web/src/
├── api/
│   └── useApiFetch.ts      # VueUse createFetch wrapper
├── features/
│   ├── login/
│   │   ├── views/LoginView.vue  # Mock login implementation
│   │   └── routes.ts
│   └── graph/
│       ├── api/graphApi.ts      # API composables
│       └── routes.ts            # Route guards (localStorage check)
└── router/index.ts
```

**What Works:**

- ✅ VueUse `createFetch` for API calls
- ✅ Login UI component
- ✅ Route navigation
- ✅ API composables pattern

**What Needs to Change:**

- ❌ Login stores mock data in localStorage
- ❌ No `credentials: 'include'` in fetch options
- ❌ No automatic token refresh on 401
- ❌ Route guards check localStorage instead of server state

---

## Authentication Flow

### 1. Login Flow

```
┌─────────┐                  ┌─────────┐                  ┌──────────┐
│ Browser │                  │   API   │                  │ Database │
└────┬────┘                  └────┬────┘                  └────┬─────┘
     │                            │                            │
     │ POST /auth/login           │                            │
     │ {email, password}          │                            │
     ├───────────────────────────>│                            │
     │                            │                            │
     │                            │ Verify credentials         │
     │                            ├───────────────────────────>│
     │                            │                            │
     │                            │ User + hashed password     │
     │                            │<───────────────────────────┤
     │                            │                            │
     │                            │ Create access token (JWT)  │
     │                            │ Create refresh token       │
     │                            │ Store hashed refresh token │
     │                            ├───────────────────────────>│
     │                            │                            │
     │ Set-Cookie: access_token   │                            │
     │ Set-Cookie: refresh_token  │                            │
     │ (HTTP-only, Secure, SameSite=Lax)                       │
     │<───────────────────────────┤                            │
     │                            │                            │
     │ {message: "success"}       │                            │
     │<───────────────────────────┤                            │
     │                            │                            │
```

### 2. Authenticated Request Flow

```
┌─────────┐                  ┌─────────┐
│ Browser │                  │   API   │
└────┬────┘                  └────┬────┘
     │                            │
     │ GET /graph/entities        │
     │ Cookie: access_token=...   │
     ├───────────────────────────>│
     │                            │
     │                            │ Verify JWT from cookie
     │                            │ Extract user info
     │                            │
     │ Response + data            │
     │<───────────────────────────┤
     │                            │
```

### 3. Token Refresh Flow (Automatic on 401)

```
┌─────────┐                  ┌─────────┐                  ┌──────────┐
│ Browser │                  │   API   │                  │ Database │
└────┬────┘                  └────┬────┘                  └────┬─────┘
     │                            │                            │
     │ GET /graph/entities        │                            │
     │ Cookie: access_token=...   │                            │
     ├───────────────────────────>│                            │
     │                            │                            │
     │                            │ JWT expired                │
     │ 401 Unauthorized           │                            │
     │<───────────────────────────┤                            │
     │                            │                            │
     │ POST /auth/refresh         │                            │
     │ Cookie: refresh_token=...  │                            │
     ├───────────────────────────>│                            │
     │                            │                            │
     │                            │ Verify refresh token       │
     │                            ├───────────────────────────>│
     │                            │                            │
     │                            │ Create new access token    │
     │                            │ Create new refresh token   │
     │                            │ Revoke old refresh token   │
     │                            │ Store new hashed token     │
     │                            ├───────────────────────────>│
     │                            │                            │
     │ Set-Cookie: access_token   │                            │
     │ Set-Cookie: refresh_token  │                            │
     │<───────────────────────────┤                            │
     │                            │                            │
     │ Retry: GET /graph/entities │                            │
     │ Cookie: access_token=...   │                            │
     ├───────────────────────────>│                            │
     │                            │                            │
     │ Response + data            │                            │
     │<───────────────────────────┤                            │
     │                            │                            │
```

### 4. Logout Flow

```
┌─────────┐                  ┌─────────┐                  ┌──────────┐
│ Browser │                  │   API   │                  │ Database │
└────┬────┘                  └────┬────┘                  └────┬─────┘
     │                            │                            │
     │ POST /auth/logout          │                            │
     │ Cookie: refresh_token=...  │                            │
     ├───────────────────────────>│                            │
     │                            │                            │
     │                            │ Revoke refresh token       │
     │                            ├───────────────────────────>│
     │                            │                            │
     │ Delete-Cookie: access_token│                            │
     │ Delete-Cookie: refresh_token                            │
     │<───────────────────────────┤                            │
     │                            │                            │
```

---

## Backend Implementation

### 1. Update Authentication Core

**File: `apps/api/app/core/authentication.py`**

Add a new function to read tokens from cookies:

```python
from fastapi import Cookie, HTTPException, status
from typing import Optional

async def get_current_user_from_cookie(
    access_token: Optional[str] = Cookie(None, alias="access_token")
) -> AuthenticatedUser:
    """Get current user from access token in HTTP-only cookie."""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(access_token)

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    role_str = payload.get("role")

    if user_id is None or role_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required user or role information",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return AuthenticatedUser(
            user_id=UUID(str(user_id)),
            tenant_id=UUID(str(tenant_id)) if tenant_id else None,
            role=UserRole(role_str),
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user, tenant, or role format in token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Create a flexible dependency that tries both methods
async def get_current_user_flexible(
    cookie_user: Optional[AuthenticatedUser] = Depends(
        lambda access_token=Cookie(None, alias="access_token"):
            get_current_user_from_cookie(access_token) if access_token else None
    ),
    header_user: Optional[AuthenticatedUser] = Depends(
        lambda credentials=Depends(security):
            get_current_user(credentials) if credentials else None
    ),
) -> AuthenticatedUser:
    """Try cookie first, fallback to header (for API keys)."""
    if cookie_user:
        return cookie_user
    if header_user:
        return header_user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
```

### 2. Update Login Endpoint

**File: `apps/api/app/features/auth/routes/login.py`**

```python
from fastapi import Response, Cookie, HTTPException, status

@router.post("/login")
async def login_for_access_token(
    response: Response,
    login_data: LoginRequest,
    use_case: LoginUseCase = Depends(get_login_use_case),
) -> dict[str, str]:
    """Authenticate user and set tokens in HTTP-only cookies."""
    result = await use_case.execute(login_data.email, login_data.password)

    # Get settings for environment-specific cookie configuration
    settings = get_settings()
    is_production = not settings.debug

    # Set access token cookie
    response.set_cookie(
        key="access_token",
        value=result.access_token,
        httponly=True,              # Not accessible to JavaScript
        secure=is_production,       # Only HTTPS in production
        samesite="lax",             # CSRF protection
        max_age=result.expires_in,  # 30 minutes
        path="/",                   # Available site-wide
    )

    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/api/v1/auth",        # Only sent to auth endpoints
    )

    return {
        "message": "Login successful",
        "token_type": "bearer"
    }
```

### 3. Update Refresh Endpoint

**File: `apps/api/app/features/auth/routes/login.py`**

```python
@router.post("/refresh")
async def refresh_access_token(
    response: Response,
    refresh_token: str = Cookie(None),
    use_case: RefreshTokenUseCase = Depends(get_refresh_token_use_case),
) -> dict[str, str]:
    """Refresh access token using refresh token from cookie."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use case returns new tokens (already implements rotation)
    result = await use_case.execute(refresh_token)

    settings = get_settings()
    is_production = not settings.debug

    # Set NEW access token cookie
    response.set_cookie(
        key="access_token",
        value=result.access_token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=result.expires_in,
        path="/",
    )

    # Set NEW refresh token cookie (rotated)
    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/api/v1/auth",
    )

    return {
        "message": "Token refreshed successfully",
        "token_type": "bearer"
    }
```

### 4. Add Logout Endpoint

**File: `apps/api/app/features/auth/routes/login.py`**

```python
@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str = Cookie(None),
) -> dict[str, str]:
    """Logout user and clear authentication cookies."""

    # Optional: Revoke refresh token in database
    if refresh_token:
        async with get_auth_db_session() as session:
            result = await session.execute(
                select(RefreshToken)
                .where(RefreshToken.revoked == False)
            )
            db_tokens = list(result.scalars().all())

            # Find and revoke the matching token
            for token in db_tokens:
                if verify_refresh_token(refresh_token, token.token_hash):
                    token.revoked = True
                    await session.commit()
                    break

    # Clear both cookies
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")

    return {"message": "Logged out successfully"}
```

### 5. Add Current User Info Endpoint

**File: `apps/api/app/features/auth/routes/login.py`**

```python
@router.get("/me")
async def get_current_user_info(
    current_user: AuthenticatedUser = Depends(get_current_user_from_cookie),
) -> dict:
    """Get current authenticated user information."""
    async with get_auth_db_session() as session:
        user = await session.get(User, current_user.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        }
```

### 6. Update Authorization Dependencies

**File: `apps/api/app/core/authorization.py`**

Update `get_tenant_from_jwt` to use the new cookie-based auth:

```python
async def get_tenant_from_jwt(
    user: AuthenticatedUser = Depends(get_current_user_from_cookie),
) -> TenantInfo | None:
    """Get tenant info from JWT authentication (now from cookie)."""
    if not user or not user.tenant_id:
        return None

    async with get_auth_db_session() as session:
        tenant = await session.get(Tenant, user.tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found for authenticated user",
            )
        return TenantInfo(tenant_id=user.tenant_id, graph_name=tenant.age_graph_name)
```

### 7. Update DTOs (Optional)

**File: `apps/api/app/features/auth/dtos/auth_dto.py`**

Keep the existing DTOs for backward compatibility, but they're no longer used for cookies:

```python
# LoginResponse and RefreshTokenResponse are now only used internally
# The endpoints return simple success messages instead

class LoginSuccessResponse(BaseModel):
    """Response model for successful login with cookies."""
    message: str
    token_type: str = "bearer"

class LogoutResponse(BaseModel):
    """Response model for successful logout."""
    message: str
```

---

## Frontend Implementation

### 1. Update `useApiFetch` Composable

**File: `apps/web/src/api/useApiFetch.ts`**

```typescript
import { createFetch } from "@vueuse/core";
import type { BeforeFetchContext, OnFetchErrorContext } from "@vueuse/core";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export const useApiFetch = createFetch({
  baseUrl: BASE_URL,
  options: {
    // Run before every fetch call
    async beforeFetch({ options }: BeforeFetchContext) {
      // Cookies are sent automatically, but we can add other logic here
      return { options };
    },

    // Handle errors, including automatic token refresh on 401
    async onFetchError(ctx: OnFetchErrorContext) {
      const { response } = ctx;

      // If we get a 401 and it's not the refresh endpoint, try to refresh
      if (
        response?.status === 401 &&
        !ctx.response?.url.includes("/auth/refresh")
      ) {
        console.log("Access token expired, attempting refresh...");

        const refreshed = await refreshAccessToken();

        if (refreshed) {
          // Retry the original request
          console.log("Token refreshed, retrying original request");
          return await ctx.execute();
        } else {
          // Refresh failed, redirect to login
          console.error("Token refresh failed, redirecting to login");
          window.location.href = "/login";
        }
      }

      // For other errors, return the context as-is
      return ctx;
    },
  },

  // Default fetch options applied to all requests
  fetchOptions: {
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include", // ⭐ Critical: Send cookies with every request
  },
});

/**
 * Refresh the access token using the refresh token cookie.
 * Returns true if successful, false otherwise.
 */
async function refreshAccessToken(): Promise<boolean> {
  try {
    const response = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include", // Send refresh_token cookie
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (response.ok) {
      console.log("Token refreshed successfully");
      return true;
    }

    console.error("Token refresh failed:", response.status);
    return false;
  } catch (error) {
    console.error("Token refresh error:", error);
    return false;
  }
}

// Export for manual refresh if needed
export { refreshAccessToken };
```

### 2. Create Authentication Composable

**File: `apps/web/src/features/login/composables/useAuth.ts`** (new file)

```typescript
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useApiFetch } from "@/api/useApiFetch";

interface LoginCredentials {
  email: string;
  password: string;
}

interface CurrentUser {
  id: string;
  email: string;
  role: string;
  tenant_id: string | null;
}

export function useAuth() {
  const router = useRouter();
  const currentUser = ref<CurrentUser | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  /**
   * Login with email and password
   */
  const login = async (credentials: LoginCredentials) => {
    isLoading.value = true;
    error.value = null;

    const {
      execute,
      statusCode,
      error: fetchError,
    } = useApiFetch("/auth/login", {
      immediate: false,
    })
      .post(credentials)
      .json<{ message: string; token_type: string }>();

    await execute();

    isLoading.value = false;

    if (statusCode.value && statusCode.value >= 200 && statusCode.value < 300) {
      // Success - tokens are in cookies, fetch user info
      await fetchCurrentUser();
      return true;
    } else {
      error.value = fetchError.value?.message || "Login failed";
      return false;
    }
  };

  /**
   * Logout and clear session
   */
  const logout = async () => {
    const { execute } = useApiFetch("/auth/logout", {
      immediate: false,
    })
      .post()
      .json();

    await execute();

    currentUser.value = null;
    router.push("/login");
  };

  /**
   * Fetch current user information
   */
  const fetchCurrentUser = async () => {
    const { execute, data, statusCode } = useApiFetch("/auth/me", {
      immediate: false,
    })
      .get()
      .json<CurrentUser>();

    await execute();

    if (statusCode.value && statusCode.value >= 200 && statusCode.value < 300) {
      currentUser.value = data.value;
      return true;
    }

    return false;
  };

  /**
   * Check if user is authenticated
   */
  const checkAuth = async () => {
    return await fetchCurrentUser();
  };

  return {
    currentUser,
    isLoading,
    error,
    login,
    logout,
    checkAuth,
  };
}
```

### 3. Update Login View

**File: `apps/web/src/features/login/views/LoginView.vue`**

```vue
<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuth } from "../composables/useAuth";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

const router = useRouter();
const { login, isLoading, error: authError } = useAuth();

// Form data
const email = ref("");
const password = ref("");
const errorMessage = ref("");

// Handle login submission
const handleLogin = async () => {
  if (!email.value || !password.value) {
    errorMessage.value = "Please fill in all fields";
    return;
  }

  errorMessage.value = "";

  const success = await login({
    email: email.value,
    password: password.value,
  });

  if (success) {
    console.log("Login successful, redirecting...");
    router.push("/");
  } else {
    errorMessage.value = authError.value || "Invalid credentials";
  }
};
</script>

<template>
  <div class="flex justify-center items-center min-h-screen bg-background p-8">
    <Card class="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Welcome Back</CardTitle>
        <CardDescription>Enter your credentials to sign in.</CardDescription>
      </CardHeader>
      <CardContent>
        <form @submit.prevent="handleLogin" class="flex flex-col gap-6">
          <div class="flex flex-col gap-2">
            <label for="email">Email</label>
            <Input
              id="email"
              v-model="email"
              type="email"
              placeholder="Enter your email"
              class="w-full"
              required
            />
          </div>

          <div class="flex flex-col gap-2">
            <label for="password">Password</label>
            <Input
              id="password"
              v-model="password"
              type="password"
              placeholder="Enter your password"
              class="w-full"
              required
            />
          </div>

          <Alert v-if="errorMessage" variant="destructive">
            <AlertDescription>
              {{ errorMessage }}
            </AlertDescription>
          </Alert>

          <Button type="submit" :disabled="isLoading" size="lg">
            <span v-if="isLoading">Signing in...</span>
            <span v-else>Sign In</span>
          </Button>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
```

### 4. Update Route Guards

**File: `apps/web/src/features/graph/routes.ts`**

```typescript
import type { RouteRecordRaw } from "vue-router";

// Check authentication by hitting the /auth/me endpoint
const checkAuth = async (): Promise<boolean> => {
  try {
    const response = await fetch("http://localhost:8000/api/v1/auth/me", {
      credentials: "include",
    });
    return response.ok;
  } catch {
    return false;
  }
};

export const graphRoutes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "Home",
    component: () => import("./views/HomeView.vue"),
    beforeEnter: async (_to, _from, next) => {
      const isAuth = await checkAuth();
      if (!isAuth) {
        console.log("Not authenticated, redirecting to login");
        next("/login");
      } else {
        next();
      }
    },
  },
];
```

### 5. Environment Configuration

**File: `apps/web/.env.development`** (new file)

```env
VITE_API_URL=http://localhost:8000/api/v1
```

**File: `apps/web/.env.production`** (new file)

```env
VITE_API_URL=https://your-production-domain.com/api/v1
```

### 6. No Changes Needed in Existing API Composables! ✅

**File: `apps/web/src/features/graph/api/graphApi.ts`**

Your existing API composables will work automatically with cookies:

```typescript
// This already works with the updated useApiFetch!
export const useFindEntityByIdentifier = (
  params: MaybeRefOrGetter<FindEntityParams>
) => {
  const url = computed(() => {
    const resolvedParams = toValue(params);
    if (!resolvedParams || !resolvedParams.value) {
      return "";
    }
    return `/graph/entities/lookup?type=${resolvedParams.type}&value=${resolvedParams.value}`;
  });

  return useApiFetch(url, {
    refetch: false,
    immediate: false,
  })
    .get()
    .json<GetEntityResponse>();
};
```

---

## Security Considerations

### 1. Cookie Security Attributes

| Attribute  | Value                                  | Purpose                                     |
| ---------- | -------------------------------------- | ------------------------------------------- |
| `HttpOnly` | `true`                                 | Prevents JavaScript access (XSS protection) |
| `Secure`   | `true` (prod)                          | Only sent over HTTPS                        |
| `SameSite` | `Lax`                                  | CSRF protection, allows normal navigation   |
| `Path`     | `/` (access), `/api/v1/auth` (refresh) | Limits cookie scope                         |
| `Max-Age`  | 30 min (access), 30 days (refresh)     | Automatic expiration                        |

### 2. XSS Protection

✅ **HTTP-only cookies**: Tokens cannot be accessed by JavaScript, even if XSS vulnerability exists
✅ **Content Security Policy**: Consider adding CSP headers to further restrict script execution
✅ **Input sanitization**: All user inputs should be sanitized (already handled by FastAPI)

### 3. CSRF Protection

✅ **SameSite=Lax**: Cookies not sent on cross-site POST requests
✅ **CORS configuration**: Only allow specific origins
⚠️ **Optional CSRF tokens**: For additional protection, consider implementing CSRF tokens for state-changing operations

### 4. Token Rotation

✅ **Refresh token rotation**: Each refresh generates new refresh token and revokes old one
✅ **Prevents replay attacks**: Old refresh tokens cannot be reused
✅ **Detects token theft**: If revoked token is used, indicates potential compromise

### 5. HTTPS Requirement

⚠️ **Production**: MUST use HTTPS with `Secure=true` cookies
✅ **Development**: Can use HTTP with `Secure=false` for local testing
⚠️ **Mixed content**: Ensure all resources loaded over HTTPS in production

### 6. Token Expiration

✅ **Short-lived access tokens**: 30 minutes reduces window of opportunity if compromised
✅ **Long-lived refresh tokens**: 30 days provides good UX balance
✅ **Automatic refresh**: Frontend automatically refreshes tokens before they expire

### 7. Rate Limiting

Consider implementing rate limiting on authentication endpoints:

- Login: 5 attempts per 15 minutes per IP
- Refresh: 10 attempts per minute per IP
- Password reset: 3 attempts per hour per email

---

## Implementation Steps

### Phase 1: Backend Changes (2-3 hours)

1. **Update authentication core** (30 min)

   - [ ] Add `get_current_user_from_cookie` function
   - [ ] Test token verification from cookies
   - [ ] Update imports in authorization module

2. **Update login endpoint** (30 min)

   - [ ] Modify `/auth/login` to set cookies
   - [ ] Remove response model or create new DTO
   - [ ] Test login flow with cookie inspection

3. **Update refresh endpoint** (30 min)

   - [ ] Modify `/auth/refresh` to read from cookie
   - [ ] Set new cookies in response
   - [ ] Test token rotation

4. **Add logout endpoint** (30 min)

   - [ ] Create `/auth/logout` endpoint
   - [ ] Implement token revocation
   - [ ] Clear cookies

5. **Add /me endpoint** (20 min)

   - [ ] Create `/auth/me` endpoint
   - [ ] Test user info retrieval

6. **Update authorization dependencies** (20 min)
   - [ ] Update `get_tenant_from_jwt` to use cookies
   - [ ] Test with protected endpoints

### Phase 2: Frontend Changes (2-3 hours)

1. **Update useApiFetch** (45 min)

   - [ ] Add `credentials: 'include'` to fetch options
   - [ ] Implement `onFetchError` with automatic refresh
   - [ ] Test automatic token refresh on 401
   - [ ] Add environment variable for API URL

2. **Create useAuth composable** (45 min)

   - [ ] Implement login function
   - [ ] Implement logout function
   - [ ] Implement checkAuth function
   - [ ] Add reactive state management

3. **Update LoginView** (30 min)

   - [ ] Integrate useAuth composable
   - [ ] Remove localStorage logic
   - [ ] Test login flow

4. **Update route guards** (30 min)

   - [ ] Replace localStorage check with API call
   - [ ] Test protected routes
   - [ ] Test redirect to login

5. **Environment configuration** (15 min)
   - [ ] Create .env files
   - [ ] Update vite.config.ts if needed
   - [ ] Document environment variables

### Phase 3: Testing (2-3 hours)

1. **Unit tests** (1 hour)

   - [ ] Test cookie setting in login endpoint
   - [ ] Test cookie reading in auth middleware
   - [ ] Test token refresh logic
   - [ ] Test logout functionality

2. **Integration tests** (1 hour)

   - [ ] Test complete login flow
   - [ ] Test automatic token refresh
   - [ ] Test protected route access
   - [ ] Test logout and session clearing

3. **Manual testing** (1 hour)
   - [ ] Test in Chrome, Firefox, Safari
   - [ ] Test cookie security attributes in DevTools
   - [ ] Test network tab for cookie behavior
   - [ ] Test expired token scenarios
   - [ ] Test logout from multiple tabs

### Phase 4: Documentation and Deployment (1 hour)

1. **Update API documentation** (30 min)

   - [ ] Document cookie-based authentication
   - [ ] Update OpenAPI/Swagger docs
   - [ ] Add security scheme documentation

2. **Update README** (20 min)

   - [ ] Document authentication approach
   - [ ] Add setup instructions
   - [ ] Document environment variables

3. **Deployment checklist** (10 min)
   - [ ] Verify HTTPS is enabled
   - [ ] Set `Secure=true` in production
   - [ ] Configure CORS for production domain
   - [ ] Set proper environment variables

---

## Testing Strategy

### Backend Tests

**File: `apps/api/tests/features/auth/routes/test_login_with_cookies.py`**

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_login_sets_cookies(client: AsyncClient, test_user):
    """Test that login endpoint sets HTTP-only cookies."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "test_password"}
    )

    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    # Verify cookie attributes
    access_cookie = response.cookies["access_token"]
    assert access_cookie.httponly
    assert access_cookie.samesite == "lax"


@pytest.mark.asyncio
async def test_refresh_with_cookie(client: AsyncClient, test_user):
    """Test that refresh endpoint reads from and sets cookies."""
    # First login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "test_password"}
    )

    # Extract cookies
    cookies = login_response.cookies

    # Refresh with cookies
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        cookies=cookies
    )

    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.cookies
    assert "refresh_token" in refresh_response.cookies

    # Verify new tokens are different
    assert refresh_response.cookies["access_token"] != cookies["access_token"]
    assert refresh_response.cookies["refresh_token"] != cookies["refresh_token"]


@pytest.mark.asyncio
async def test_authenticated_request_with_cookie(client: AsyncClient, test_user):
    """Test accessing protected endpoint with cookie."""
    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "test_password"}
    )

    cookies = login_response.cookies

    # Access protected endpoint
    me_response = await client.get(
        "/api/v1/auth/me",
        cookies=cookies
    )

    assert me_response.status_code == 200
    data = me_response.json()
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_logout_clears_cookies(client: AsyncClient, test_user):
    """Test that logout clears cookies."""
    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "test_password"}
    )

    cookies = login_response.cookies

    # Logout
    logout_response = await client.post(
        "/api/v1/auth/logout",
        cookies=cookies
    )

    assert logout_response.status_code == 200

    # Verify cookies are cleared (max_age=0 or expired)
    # Implementation depends on your HTTP client
```

### Frontend Tests

**File: `apps/web/src/features/login/composables/__tests__/useAuth.spec.ts`**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAuth } from "../useAuth";

describe("useAuth", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should login successfully with valid credentials", async () => {
    // Mock fetch
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ message: "Login successful" }),
      } as Response)
    );

    const { login, currentUser } = useAuth();
    const success = await login({
      email: "test@example.com",
      password: "password123",
    });

    expect(success).toBe(true);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/auth/login"),
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      })
    );
  });

  it("should handle login failure", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: "Invalid credentials" }),
      } as Response)
    );

    const { login, error } = useAuth();
    const success = await login({
      email: "test@example.com",
      password: "wrong",
    });

    expect(success).toBe(false);
    expect(error.value).toBeTruthy();
  });

  it("should check authentication status", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            id: "123",
            email: "test@example.com",
            role: "TENANT_USER",
          }),
      } as Response)
    );

    const { checkAuth, currentUser } = useAuth();
    const isAuth = await checkAuth();

    expect(isAuth).toBe(true);
    expect(currentUser.value).toBeTruthy();
    expect(currentUser.value?.email).toBe("test@example.com");
  });
});
```

---

## Migration Considerations

### Backward Compatibility

For a smooth transition, you can support both authentication methods temporarily:

1. **Accept tokens from both cookie and header**
2. **Gradually migrate clients to cookie-based auth**
3. **Remove header-based auth after migration period**

### Existing Sessions

- Users with existing tokens in localStorage will need to re-login
- Consider adding a migration notice in the UI
- Clear localStorage on first load of new version

### API Clients

- Mobile apps might prefer header-based auth (easier than cookie management)
- Keep API key authentication for service-to-service communication
- Document both authentication methods

---

## Monitoring and Observability

### Metrics to Track

1. **Authentication success/failure rates**
2. **Token refresh frequency**
3. **Average session duration**
4. **Failed refresh attempts (potential security issue)**
5. **Logout frequency**

### Logging

Log the following events:

- Successful logins (user ID, IP, timestamp)
- Failed login attempts (email, IP, reason, timestamp)
- Token refreshes (user ID, timestamp)
- Logouts (user ID, timestamp)
- Suspicious activity (multiple failed refresh attempts)

### Alerts

Set up alerts for:

- Unusual spike in failed logins
- High rate of failed token refreshes
- Potential credential stuffing attacks

---

## Future Enhancements

### Short Term

1. **Remember Me**: Extend refresh token expiration for opted-in users
2. **Session Management**: List active sessions, revoke specific sessions
3. **Two-Factor Authentication**: Add TOTP or SMS-based 2FA
4. **Password Reset**: Implement secure password reset flow

### Long Term

1. **OAuth2/OIDC**: Support social login (Google, GitHub, etc.)
2. **Biometric Authentication**: WebAuthn for passwordless login
3. **Device Fingerprinting**: Track and verify known devices
4. **Anomaly Detection**: ML-based detection of unusual login patterns

---

## Conclusion

This authentication implementation using HTTP-only cookies provides a secure, scalable, and user-friendly authentication system. The key benefits are:

✅ **Security First**: XSS-proof token storage
✅ **Seamless UX**: Automatic token refresh, persistent sessions
✅ **Clean Architecture**: Separation of concerns, testable code
✅ **Future-Proof**: Easy to extend with additional auth methods

### Success Criteria

- [ ] All authentication endpoints use cookies
- [ ] Frontend automatically refreshes tokens
- [ ] Protected routes require authentication
- [ ] Logout clears all session data
- [ ] All tests passing
- [ ] Security audit completed
- [ ] Documentation updated

### Timeline

**Total Estimated Time**: 8-10 hours

- Backend: 2-3 hours
- Frontend: 2-3 hours
- Testing: 2-3 hours
- Documentation: 1 hour

### Next Steps

1. Review this plan with the team
2. Set up development environment
3. Start with Phase 1 (Backend Changes)
4. Test thoroughly at each phase
5. Deploy to staging for integration testing
6. Deploy to production with monitoring

---

**Document Version**: 1.0
**Last Updated**: October 29, 2025
**Author**: Development Team
**Status**: Ready for Implementation
