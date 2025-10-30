import { createFetch } from "@vueuse/core";
import type { BeforeFetchContext } from "@vueuse/core";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export const useApiFetch = createFetch({
  baseUrl: BASE_URL,
  options: {
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
    credentials: "include", // ⭐ Critical: Send cookies with every request
  },
});

/**
 * Refresh the access token using the refresh token cookie.
 * Returns true if successful, false otherwise.
 *
 * Note: This is exported for manual use, but automatic refresh has been disabled.
 */
export async function refreshAccessToken(): Promise<boolean> {
  try {
    console.log("Attempting to refresh token at:", `${BASE_URL}/auth/refresh`);
    const response = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include", // Send refresh_token cookie
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (response.ok) {
      const data = await response.json();
      console.log("Token refreshed successfully:", data);
      return true;
    }

    // Log detailed error information
    const errorText = await response.text();
    console.error("Token refresh failed:", {
      status: response.status,
      statusText: response.statusText,
      error: errorText,
    });
    return false;
  } catch (error) {
    console.error("Token refresh error:", error);
    return false;
  }
}
