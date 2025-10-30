import { useApiFetch } from "@/api/useApiFetch";

export interface LoginCredentials {
  email: string;
  password: string;
}

export type UserRole = "super_admin" | "tenant_admin" | "tenant_user";

export interface CurrentUser {
  id: string;
  email: string;
  role: UserRole;
  tenant_id: string | null;
}

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
