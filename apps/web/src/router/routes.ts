import type { RouteRecordRaw } from "vue-router";
import { requireAuth, requireRole, redirectAuthenticatedUser } from "./guards";

export const routes: RouteRecordRaw[] = [
  // ==================== ROOT REDIRECT ====================
  {
    path: "/",
    beforeEnter: async (_to, _from, next) => {
      const { fetchCurrentUser } = await import("@/api/authApi");
      const user = await fetchCurrentUser();

      if (!user) return next("/login");

      switch (user.role) {
        case "super_admin":
          return next("/tenants");
        case "tenant_admin":
          return next("/users");
        default:
          return next("/graph");
      }
    },
    component: () => import("@/pages/login/views/LoginView.vue"), // Placeholder, never shown
  },

  // ==================== AUTH ====================
  {
    path: "/login",
    name: "Login",
    component: () => import("@/pages/login/views/LoginView.vue"),
    beforeEnter: redirectAuthenticatedUser,
  },

  // ==================== GRAPH EXPLORER ====================
  {
    path: "/graph",
    name: "GraphExplorer",
    component: () => import("@/pages/graph/views/GraphExplorerView.vue"),
    beforeEnter: [requireAuth, requireRole(["tenant_admin", "tenant_user"])],
  },

  // ==================== TENANTS MANAGEMENT ====================
  {
    path: "/tenants",
    name: "TenantsManagement",
    component: () => import("@/pages/tenants/views/TenantsManagementView.vue"),
    beforeEnter: [requireAuth, requireRole(["super_admin"])],
  },

  // ==================== USERS MANAGEMENT ====================
  {
    path: "/users",
    name: "UsersManagement",
    component: () => import("@/pages/users/views/UsersManagementView.vue"),
    beforeEnter: [requireAuth, requireRole(["tenant_admin"])],
  },
];
