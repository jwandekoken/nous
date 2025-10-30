import { ref } from "vue";
import { useRouter } from "vue-router";
import {
  fetchCurrentUser as fetchCurrentUserFromApi,
  login as loginUser,
  logout as logoutUser,
} from "@/api/authApi";
import type { LoginCredentials, CurrentUser } from "@/api/authApi";

export function useAuth() {
  const router = useRouter();
  const currentUser = ref<CurrentUser | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  /**
   * Login with email and password
   */
  const login = async (credentials: LoginCredentials) => {
    isLoading.value = true;
    error.value = null;

    const { execute, statusCode, error: fetchError } = loginUser(credentials);

    await execute();

    isLoading.value = false;

    if (statusCode.value && statusCode.value >= 200 && statusCode.value < 300) {
      // Success - tokens are in cookies, we can navigate to the home page
      return true;
    } else {
      error.value = fetchError.value?.message || "Login failed";
      return false;
    }
  };

  /**
   * Logout and clear session
   */
  const logout = async () => {
    const { execute } = logoutUser();

    await execute();

    currentUser.value = null;
    router.push("/login");
  };

  /**
   * Fetch current user information
   */
  const fetchCurrentUser = async () => {
    const user = await fetchCurrentUserFromApi();
    if (user) {
      currentUser.value = user;
      return true;
    }
    return false;
  };

  return {
    currentUser,
    isLoading,
    error,
    login,
    logout,
    fetchCurrentUser,
  };
}
