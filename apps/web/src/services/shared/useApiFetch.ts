import { createFetch } from "@vueuse/core";
import type { BeforeFetchContext } from "@vueuse/core";
import { refreshTokens } from "@/services/auth/refreshTokens";
import { emitSessionExpired } from "@/services/auth/sessionEvents";

const DEFAULT_API_URL = "http://localhost:8000/api/v1";
const BASE_URL = import.meta.env.VITE_API_URL || DEFAULT_API_URL;
const FALLBACK_ORIGIN =
  typeof window !== "undefined" ? window.location.origin : "http://localhost";

const apiBaseUrl = (() => {
  try {
    return new URL(BASE_URL, FALLBACK_ORIGIN);
  } catch {
    return new URL(DEFAULT_API_URL);
  }
})();

const apiBasePath = (() => {
  const path = apiBaseUrl.pathname.endsWith("/")
    ? apiBaseUrl.pathname.slice(0, -1)
    : apiBaseUrl.pathname;
  return path === "/" ? "" : path;
})();

const EXCLUDED_REFRESH_ENDPOINTS = new Set([
  "/auth/login",
  "/auth/logout",
  "/auth/refresh",
]);

const SESSION_EXPIRED_MESSAGE = "Session expired. Please sign in again.";

let refreshingPromise: Promise<boolean> | null = null;

const shouldAttemptRefresh = (url: string) => {
  try {
    const targetUrl = new URL(url, apiBaseUrl);

    if (targetUrl.origin !== apiBaseUrl.origin) {
      return false;
    }

    if (apiBasePath && !targetUrl.pathname.startsWith(apiBasePath)) {
      return false;
    }

    let relativePath = apiBasePath
      ? targetUrl.pathname.slice(apiBasePath.length)
      : targetUrl.pathname;

    if (!relativePath.startsWith("/")) {
      relativePath = `/${relativePath}`;
    }

    return !EXCLUDED_REFRESH_ENDPOINTS.has(relativePath);
  } catch (error) {
    console.error("Failed to parse request URL for refresh handling", error);
    return false;
  }
};

const attemptTokenRefresh = async () => {
  if (!refreshingPromise) {
    refreshingPromise = refreshTokens()
      .then(() => true)
      .catch((error) => {
        console.error("Token refresh failed", error);
        return false;
      })
      .finally(() => {
        refreshingPromise = null;
      });
  }

  return refreshingPromise;
};

const guardedFetch: typeof fetch = async (input, init) => {
  const request = new Request(input, init);
  let response = await fetch(request.clone());
  let hasRetried = false;

  while (
    response.status === 401 &&
    !hasRetried &&
    shouldAttemptRefresh(request.url)
  ) {
    const refreshed = await attemptTokenRefresh();

    if (!refreshed) {
      emitSessionExpired(SESSION_EXPIRED_MESSAGE);
      return response;
    }

    hasRetried = true;
    response = await fetch(request.clone());
  }

  return response;
};

export const useApiFetch = createFetch({
  baseUrl: BASE_URL,
  options: {
    fetch: guardedFetch,
    // Run before every fetch call
    async beforeFetch({ options }: BeforeFetchContext) {
      // Cookies are sent automatically, but we can add other logic here
      return { options };
    },
  },

  // Default fetch options applied to all requests
  fetchOptions: {
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include", // Critical: Send cookies with every request
  },
});
