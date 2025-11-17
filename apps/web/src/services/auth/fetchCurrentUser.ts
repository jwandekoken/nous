import { useApiFetch } from "@/services/shared";
import type { CurrentUser } from "./types";

/**
 * Fetches the current user from the API.
 * @returns {Promise<CurrentUser | null>} The user object or null if not authenticated.
 */
export const fetchCurrentUser = async (): Promise<CurrentUser | null> => {
  const { execute, data, statusCode } = useApiFetch("/auth/me", {
    immediate: false,
  })
    .get()
    .json<CurrentUser>();

  await execute();

  if (statusCode.value === 200 && data.value) {
    return data.value;
  }

  return null;
};
