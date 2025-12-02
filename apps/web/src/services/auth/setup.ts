import { useApiFetch } from "@/services/shared";
import type {
  SetupAdminRequest,
  SetupAdminResponse,
  SetupRequiredResponse,
} from "./types";

/**
 * Checks if the application requires initial setup (no super admin exists).
 */
export const checkSetupRequired = () => {
  return useApiFetch("/auth/setup-required")
    .get()
    .json<SetupRequiredResponse>();
};

/**
 * Creates the first super admin user.
 */
export const setupAdmin = (data: SetupAdminRequest) => {
  return useApiFetch("/auth/setup-admin", {
    immediate: false,
  })
    .post(data)
    .json<SetupAdminResponse>();
};
