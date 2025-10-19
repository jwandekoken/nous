import type { RouteRecordRaw } from "vue-router";

// Lazy-load the view components for better performance
const LoginView = () => import("./views/LoginView.vue");

export const loginRoutes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: LoginView,
  },
];
