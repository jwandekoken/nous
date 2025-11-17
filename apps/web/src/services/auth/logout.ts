import { useApiFetch } from "@/services/shared";

/**
 * Logs out the current user.
 */
export const logout = () => {
  return useApiFetch("/auth/logout", {
    immediate: false,
  })
    .post()
    .json();
};
