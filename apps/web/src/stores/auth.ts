import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useSessionStorage } from "@vueuse/core";
import { useRouter } from "vue-router";
import {
  login as loginUser,
  logout as logoutUser,
  fetchCurrentUser as fetchCurrentUserFromApi,
  type LoginCredentials,
  type CurrentUser,
} from "@/api/authApi";

export const useAuthStore = defineStore("auth", () => {
  const router = useRouter();

  // State - currentUser synced with session storage
  const currentUser = useSessionStorage<CurrentUser | null>("auth:user", null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

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

    router.push("/login");
  };

  const fetchUser = async (): Promise<CurrentUser | null> => {
    // If user is already cached in session storage, return it
    if (currentUser.value) {
      return currentUser.value;
    }

    // Otherwise, fetch from API
    const user = await fetchCurrentUserFromApi();

    if (user) {
      // Store in session storage (automatically synced via useSessionStorage)
      currentUser.value = user;
      return user;
    }

    return null;
  };

  const clearError = () => {
    error.value = null;
  };

  return {
    // State
    currentUser,
    isLoading,
    error,
    // Getters
    isAuthenticated,
    userRole,
    // Actions
    login,
    logout,
    fetchUser,
    clearError,
  };
});
