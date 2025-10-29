import { ref } from "vue";
import { useRouter } from "vue-router";
import { useApiFetch } from "@/api/useApiFetch";

interface LoginCredentials {
  email: string;
  password: string;
}

interface CurrentUser {
  id: string;
  email: string;
  role: string;
  tenant_id: string | null;
}

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

    const {
      execute,
      statusCode,
      error: fetchError,
    } = useApiFetch("/auth/login", {
      immediate: false,
    })
      .post(credentials)
      .json<{ message: string; token_type: string }>();

    await execute();

    isLoading.value = false;

    if (statusCode.value && statusCode.value >= 200 && statusCode.value < 300) {
      // Success - tokens are in cookies, fetch user info
      await fetchCurrentUser();
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
    const { execute } = useApiFetch("/auth/logout", {
      immediate: false,
    })
      .post()
      .json();

    await execute();

    currentUser.value = null;
    router.push("/login");
  };

  /**
   * Fetch current user information
   */
  const fetchCurrentUser = async () => {
    const { execute, data, statusCode } = useApiFetch("/auth/me", {
      immediate: false,
    })
      .get()
      .json<CurrentUser>();

    await execute();

    if (statusCode.value && statusCode.value >= 200 && statusCode.value < 300) {
      currentUser.value = data.value;
      return true;
    }

    return false;
  };

  /**
   * Check if user is authenticated
   */
  const checkAuth = async () => {
    return await fetchCurrentUser();
  };

  return {
    currentUser,
    isLoading,
    error,
    login,
    logout,
    checkAuth,
  };
}
