import type { NavigationGuardNext, RouteLocationNormalized } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import type { UserRole } from "@/api/authApi";

/**
 * Requires authentication to access route
 */
export const requireAuth = async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) => {
  const authStore = useAuthStore();

  // Check if user is already cached in store (from session storage)
  if (!authStore.currentUser) {
    // Try to fetch user (will check session storage first, then API)
    await authStore.fetchUser();
  }

  if (!authStore.currentUser) {
    console.log("Not authenticated, redirecting to login");
    next("/login");
  } else {
    next();
  }
};

/**
 * Requires specific role(s) to access route
 */
export const requireRole = (allowedRoles: UserRole[]) => {
  return async (
    to: RouteLocationNormalized,
    from: RouteLocationNormalized,
    next: NavigationGuardNext
  ) => {
    const authStore = useAuthStore();

    // User should already be fetched by requireAuth guard
    // But double-check just in case
    if (!authStore.currentUser) {
      await authStore.fetchUser();
    }

    if (!authStore.currentUser) {
      return next("/login");
    }

    if (!allowedRoles.includes(authStore.currentUser.role)) {
      console.warn(
        `User role ${authStore.currentUser.role} not allowed for this route`
      );
      return next("/"); // Redirect to home (which will redirect to appropriate page)
    }

    next();
  };
};

/**
 * Redirects authenticated users away from login page
 */
export const redirectAuthenticatedUser = async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) => {
  const authStore = useAuthStore();

  if (authStore.currentUser) {
    // User is authenticated, redirect to their role-appropriate page
    switch (authStore.currentUser.role) {
      case "super_admin":
        return next("/tenants");
      case "tenant_admin":
        return next("/users");
      default:
        return next("/graph");
    }
  }
  next();
};
