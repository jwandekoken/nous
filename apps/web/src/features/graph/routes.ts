import type { RouteRecordRaw } from "vue-router";

// Lazy-load the view components for better performance
const EntitySearchView = () => import("./views/EntitySearchView.vue");
const EntityDetailView = () => import("./views/EntityDetailView.vue");

export const graphRoutes: RouteRecordRaw[] = [
  {
    path: "/graph/search",
    name: "EntitySearch",
    component: EntitySearchView,
  },
  {
    // Example with dynamic segment for entity ID
    path: "/graph/entity/:id",
    name: "EntityDetail",
    component: EntityDetailView,
    props: true, // Pass route params as component props
  },
];
