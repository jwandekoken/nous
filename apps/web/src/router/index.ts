import { createRouter, createWebHistory } from "vue-router";
import { routes } from "./routes";

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to, _from, next) => {
  // Dynamically import store to avoid circular dependencies or early access issues
  const { useAuthStore } = await import("@/stores/auth");
  const authStore = useAuthStore();

  try {
    const isSetupRequired = await authStore.checkSetupRequired();

    if (isSetupRequired) {
      if (to.path !== "/setup") {
        return next("/setup");
      }
    } else {
      if (to.path === "/setup") {
        return next("/login");
      }
    }
    next();
  } catch (error) {
    console.error("Router guard error:", error);
    next();
  }
});

export default router;
