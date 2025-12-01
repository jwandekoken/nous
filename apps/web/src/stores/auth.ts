import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useSessionStorage } from "@vueuse/core";
import { useRouter } from "vue-router";
import { toast } from "vue-sonner";
import {
  login as loginUser,
  logout as logoutUser,
  fetchCurrentUser as fetchCurrentUserFromApi,
  refreshTokens,
  checkSetupRequired as checkSetupRequiredApi,
  setupAdmin as setupAdminApi,
  type LoginCredentials,
  type CurrentUser,
  type SetupAdminRequest,
} from "@/services/auth";
import { onSessionExpired } from "@/services/auth/sessionEvents";

const SESSION_EXPIRED_MESSAGE = "Session expired. Please sign in again.";
const DISABLE_REFRESH_SCHEDULER =
  import.meta.env.VITE_DISABLE_REFRESH_SCHEDULER === "true";
const ACCESS_TOKEN_TTL_MS = Number(
  import.meta.env.VITE_ACCESS_TOKEN_TTL_MS ?? 30 * 60 * 1000
);
const REFRESH_SAFETY_WINDOW_MS = Number(
  import.meta.env.VITE_REFRESH_SCHEDULER_LEEWAY_MS ?? 5 * 60 * 1000
);
const REFRESH_INTERVAL_MS = Math.max(
  REFRESH_SAFETY_WINDOW_MS,
  ACCESS_TOKEN_TTL_MS - REFRESH_SAFETY_WINDOW_MS
);

export const useAuthStore = defineStore("auth", () => {
  const router = useRouter();

  // State - currentUser synced with session storage
  // Explicitly provide serializer to ensure proper JSON storage
  const currentUser = useSessionStorage<CurrentUser | null>("auth:user", null, {
    serializer: {
      read: (v: string) => (v ? JSON.parse(v) : null),
      write: (v: CurrentUser | null) => JSON.stringify(v),
    },
  });

  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const isSetupRequired = ref<boolean | null>(null);
  let refreshSchedulerId: ReturnType<typeof setTimeout> | null = null;

  const clearRefreshScheduler = () => {
    if (refreshSchedulerId) {
      clearTimeout(refreshSchedulerId);
      refreshSchedulerId = null;
    }
  };

  const scheduleTokenRefresh = () => {
    if (DISABLE_REFRESH_SCHEDULER || !currentUser.value) {
      return;
    }

    clearRefreshScheduler();

    refreshSchedulerId = window.setTimeout(async () => {
      try {
        await refreshTokens();
        scheduleTokenRefresh();
      } catch (err) {
        console.error("Scheduled token refresh failed", err);
        await handleSessionExpiration();
      }
    }, REFRESH_INTERVAL_MS);
  };

  const handleSessionExpiration = async (
    message: string = SESSION_EXPIRED_MESSAGE
  ) => {
    clearRefreshScheduler();
    currentUser.value = null;
    error.value = message;

    toast.error(message);

    if (router.currentRoute.value.path !== "/login") {
      await router.push("/login");
    }
  };

  onSessionExpired((message) => {
    void handleSessionExpiration(message);
  });

  // Getters
  const isAuthenticated = computed(() => !!currentUser.value);
  const userRole = computed(() => currentUser.value?.role);

  // Actions
  const login = async (credentials: LoginCredentials): Promise<boolean> => {
    isLoading.value = true;
    error.value = null;

    const { execute, statusCode, error: fetchError } = loginUser(credentials);

    await execute();

    isLoading.value = false;

    if (statusCode.value && statusCode.value >= 200 && statusCode.value < 300) {
      // Success - fetch user data and store in session storage
      await fetchUser();
      return true;
    } else {
      error.value = fetchError.value?.message || "Login failed";
      return false;
    }
  };

  const logout = async () => {
    const { execute } = logoutUser();

    await execute();

    // Clear session storage and state
    currentUser.value = null;
    error.value = null;
    clearRefreshScheduler();

    router.push("/login");
  };

  const fetchUser = async (): Promise<CurrentUser | null> => {
    // If user is already cached in session storage AND has all required fields, return it
    if (currentUser.value?.id && currentUser.value?.role) {
      scheduleTokenRefresh();
      return currentUser.value;
    }

    // Otherwise, fetch from API
    const user = await fetchCurrentUserFromApi();

    if (user) {
      // Store in session storage (automatically synced via useSessionStorage)
      currentUser.value = user;
      scheduleTokenRefresh();
      return user;
    }

    return null;
  };

  const checkSetupRequired = async (): Promise<boolean> => {
    if (isSetupRequired.value !== null) {
      return isSetupRequired.value;
    }

    const { data, error: fetchError } = await checkSetupRequiredApi();

    if (fetchError.value) {
      console.error("Failed to check setup requirement", fetchError.value);
      // Default to false to avoid blocking if API fails? Or true to be safe?
      // Let's assume false if we can't reach API, or maybe we should let it fail.
      // For now, let's just return false but not cache it if error.
      return false;
    }

    if (data.value) {
      isSetupRequired.value = data.value.setup_required;
      return data.value.setup_required;
    }

    return false;
  };

  const setupAdmin = async (data: SetupAdminRequest): Promise<boolean> => {
    isLoading.value = true;
    error.value = null;

    const { execute, statusCode, error: fetchError } = setupAdminApi(data);

    await execute();

    isLoading.value = false;

    // Check if statusCode is available and indicates success
    if (statusCode.value && statusCode.value >= 200 && statusCode.value < 300) {
      isSetupRequired.value = false;
      return true;
    } else {
      // If statusCode is missing or indicates failure
      error.value = fetchError.value?.message || "Setup failed";
      return false;
    }
  };

  const clearError = () => {
    error.value = null;
  };

  return {
    // State
    currentUser,
    isLoading,
    error,
    isSetupRequired,
    // Getters
    isAuthenticated,
    userRole,
    // Actions
    login,
    logout,
    fetchUser,
    clearError,
    checkSetupRequired,
    setupAdmin,
  };
});
