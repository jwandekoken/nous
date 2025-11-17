import { useApiFetch } from "@/services/shared";
import type { LoginCredentials } from "./types";

/**
 * Logs in the user with the given credentials.
 */
export const login = (credentials: LoginCredentials) => {
  return useApiFetch("/auth/login", {
    immediate: false,
  })
    .post(credentials)
    .json<{ message: string; token_type: string }>();
};
