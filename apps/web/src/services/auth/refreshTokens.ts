import type { RefreshTokensResponse } from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

/**
 * Refresh the access token using the refresh token cookie.
 * Returns the refresh payload when successful.
 */
export const refreshTokens = async (): Promise<RefreshTokensResponse> => {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Token refresh failed (${response.status} ${response.statusText}): ${errorText}`
    );
  }

  return response.json() as Promise<RefreshTokensResponse>;
};
