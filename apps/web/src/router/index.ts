import { createRouter, createWebHistory } from "vue-router";
import { graphRoutes } from "@/features/graph/routes";
import { loginRoutes } from "@/features/login/routes";

// Mock authentication - replace with real auth logic later
const isAuthenticated = () => {
  // Mock: check localStorage or return false for demo
  return localStorage.getItem("isLoggedIn") === "true";
};

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "Home",
      component: () => import("@/components/layout/MainLayout.vue"),
      beforeEnter: (_to, _from, next) => {
        // Redirect to login if not authenticated
        if (!isAuthenticated()) {
          next("/login");
        } else {
          next();
        }
      },
    },
    ...graphRoutes,
    ...loginRoutes,
  ],
});

export default router;
