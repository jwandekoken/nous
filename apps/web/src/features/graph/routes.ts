import type { RouteRecordRaw } from "vue-router";

// Check authentication by hitting the /auth/me endpoint
const checkAuth = async (): Promise<boolean> => {
  try {
    const BASE_URL =
      import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
    const response = await fetch(`${BASE_URL}/auth/me`, {
      credentials: "include",
    });
    return response.ok;
  } catch {
    return false;
  }
};

export const graphRoutes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "Home",
    component: () => import("./views/HomeView.vue"),
    beforeEnter: async (_to, _from, next) => {
      const isAuth = await checkAuth();
      if (!isAuth) {
        console.log("Not authenticated, redirecting to login");
        next("/login");
      } else {
        next();
      }
    },
  },
];
