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
        !ctx.response?.url.includes("/auth/refresh") &&
        !ctx.response?.url.includes("/auth/login")
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
