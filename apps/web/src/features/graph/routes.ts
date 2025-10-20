import type { RouteRecordRaw } from "vue-router";

// Mock authentication - replace with real auth logic later
const isAuthenticated = () => {
  // Mock: check localStorage or return false for demo
  return localStorage.getItem("isLoggedIn") === "true";
};

export const graphRoutes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "Home",
    component: () => import("./views/HomeView.vue"),
    beforeEnter: (_to, _from, next) => {
      // Redirect to login if not authenticated
      if (!isAuthenticated()) {
        next("/login");
      } else {
        next();
      }
    },
  },
];
