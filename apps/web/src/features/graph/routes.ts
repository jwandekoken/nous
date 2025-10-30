import type { RouteRecordRaw } from "vue-router";
import { fetchCurrentUser } from "@/features/login/api/authApi";

export const graphRoutes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "Home",
    component: () => import("./views/HomeView.vue"),
    beforeEnter: async (_to, _from, next) => {
      const user = await fetchCurrentUser();
      if (!user) {
        console.log("Not authenticated, redirecting to login");
        next("/login");
      } else {
        next();
      }
    },
  },
];
