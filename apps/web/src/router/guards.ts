import type { NavigationGuardNext, RouteLocationNormalized } from "vue-router";
import { fetchCurrentUser, type UserRole } from "@/api/authApi";

/**
 * Requires authentication to access route
 */
export const requireAuth = async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) => {
  const user = await fetchCurrentUser();
  if (!user) {
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
    const user = await fetchCurrentUser();

    if (!user) {
      return next("/login");
    }

    if (!allowedRoles.includes(user.role)) {
      console.warn(`User role ${user.role} not allowed for this route`);
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
  const user = await fetchCurrentUser();
  if (user) {
    // User is authenticated, redirect to their role-appropriate page
    switch (user.role) {
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
