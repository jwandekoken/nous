import { createRouter, createWebHistory } from "vue-router";
import { graphRoutes } from "@/features/graph/routes";
import { loginRoutes } from "@/features/login/routes";

const router = createRouter({
  history: createWebHistory(),
  routes: [...graphRoutes, ...loginRoutes],
});

export default router;
