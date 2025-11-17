# Auth Token Rotation Plan

## Context

- Access tokens issued by `/auth/login` expire after ~30 minutes, but the frontend only authenticates once per page load.
- Refresh tokens (30-day HTTP-only cookies) are already issued and `/auth/refresh` rotates both tokens, yet the web client never calls it automatically.
- `useApiFetch` centralizes network calls and currently exports a manual `refreshAccessToken()` helper but nothing consumes it, so any request after the access cookie expires raises a 401 and forces a full re-login.

## Objectives

1. Refresh access tokens transparently before or immediately after they expire so authenticated sessions stay valid.
2. Keep refresh logic centralized (single implementation point) to avoid duplicating retry code across services/stores.
3. Provide graceful degradation: if refresh fails (revoked token, expired refresh cookie), clear client state and send the user back to `/login`.

## Proposed Implementation

### 1. Formalize Auth Service APIs

- Break `apps/web/src/services/auth/authService.ts` into function-specific modules:
  - `apps/web/src/services/auth/login.ts`
  - `apps/web/src/services/auth/logout.ts`
  - `apps/web/src/services/auth/fetchCurrentUser.ts`
  - `apps/web/src/services/auth/refreshTokens.ts`
- Move the fetch logic that lives in `refreshAccessToken()` into `refreshTokens.ts`. This file must **not** import `useApiFetch`; it should issue a direct `fetch` so it stays dependency-free.
- Update `apps/web/src/services/auth/index.ts` to re-export all four helpers plus the existing types, keeping the public API unchanged for stores/components.
- Return a typed payload (e.g., `{ message, token_type }`) to keep parity with `/auth/login`.

### 2. Add Automatic 401 Recovery in `useApiFetch`

- Extend `createFetch` options with `afterFetch` / `onFetchError` hooks.
- On every response, detect `401`:
  1. If a refresh attempt is not already in progress, acquire a simple mutex (e.g., module-level `let refreshingPromise: Promise<boolean> | null`).
  2. Call `refreshTokens()` imported from `@/services/auth/refreshTokens`. Because this helper has no dependency on `useApiFetch`, it prevents circular imports.
  3. If refresh fails, reject the request so callers can handle logout.
- Ensure the retry path propagates the retried response back to the original caller. VueUse’s `createFetch` lets us return `{ data, response }` from hooks.
- Guard against infinite loops by only retrying once per request.

### 3. Proactive Refresh Scheduler (Optional but Recommended)

- When `login()` resolves successfully (and whenever `fetchUser()` hydrates an existing user), start a `setTimeout` (or `useIntervalFn`) that calls `refreshTokens()` ~5 minutes before the access token TTL.
- Store the timer ID in the Pinia store; reset/cancel it on `logout()`.
- Allow developers to disable the scheduler via an env flag (useful for debugging or if backend TTL changes). Expose the following knobs:
  - `VITE_DISABLE_REFRESH_SCHEDULER` (`"true"` disables timers entirely)
  - `VITE_ACCESS_TOKEN_TTL_MS` (defaults to 30 minutes)
  - `VITE_REFRESH_SCHEDULER_LEEWAY_MS` (defaults to 5 minutes before TTL elapses)

### 4. Application Bootstrap

- On app startup (e.g., router guard or root layout), call `authStore.fetchUser()`. If it returns a user, also kick the scheduler so returning users don’t wait for the first request to refresh.
- Handle SSR/CSR differences if applicable (currently CSR-only).

### 5. Failure Handling & UX

- Centralize the fallback path: if `refreshTokens()` returns false or 401 persists after retry, Pinia store should:
  - Clear `currentUser` session storage.
  - Redirect to `/login`.
  - Optionally show a toast: “Session expired. Please sign in again.”
- Expose a lightweight event emitter (e.g., `sessionEvents.ts`) that `useApiFetch` can call to signal “refresh failed” without importing the store directly; the store subscribes and executes the fallback flow.
- Consider logging refresh failures (Sentry/console) with enough context for debugging but no sensitive data.

### 6. Validation Plan

- **Unit / Integration**
  - Mock `useApiFetch` request returning 401, assert it triggers `refreshTokens()` and retries.
  - Test mutex logic to ensure concurrent requests share a single refresh call.
  - Verify scheduler fires at expected interval (can expose helper to compute delay).
- **Manual**
  - Sign in, wait 30+ minutes or manually shorten backend TTL.
  - Trigger an API call; confirm it transparently refreshes and succeeds.
  - Revoke refresh token server-side; confirm user gets redirected to login with toast.

### 7. Rollout / Observability

- Feature flag the scheduler if needed for phased rollout.
- Add temporary logging or metrics around refresh success/failure counts to ensure the new flow works in production.

## Dependencies & Risks

- Requires confidence that `/auth/refresh` rotates tokens idempotently (already true server-side).
- Need to confirm Vite env `VITE_API_URL` is correct for calling refresh preflight.
- Ensure mutex implementation doesn’t leak memory (clear references once resolved).
- Be mindful of tab concurrency: multiple tabs may still trigger refresh simultaneously; server rotation already invalidates prior refresh tokens, so critique failure paths carefully.

## Definition of Done

- Automatic refresh on 401 implemented and covered by tests.
- Optional scheduler implemented or deferred with comment explaining why.
- User experience verified manually; documentation updated (README or docs entry referencing this plan).
