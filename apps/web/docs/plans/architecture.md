## Recommended Project Structure

I recommend refactoring your current `apps/web/src` directory from the default Vite starter into a **feature-based architecture**. This will keep your code organized as the application grows and align perfectly with your backend's structure.

Here is the proposed folder structure:

```plaintext
/apps/web/src/
|
|-- api/
|   |-- index.ts            # Axios/fetch client setup, interceptors, etc.
|   `-- graphApi.ts         # API functions related to the graph feature
|
|-- assets/                 # Static assets like images, fonts, global CSS
|   `-- styles/
|       |-- main.css
|       `-- _variables.css
|
|-- components/             # Global, shared, reusable components (e.g., Button, Modal, Layout)
|   |-- layout/
|   |   |-- AppHeader.vue
|   |   `-- MainLayout.vue
|   `-- ui/
|       |-- AppButton.vue
|       `-- LoadingSpinner.vue
|
|-- features/               # CORE: Each business feature gets its own module
|   `-- graph/
|       |-- components/     # Components specific to the graph feature
|       |   |-- EntityCard.vue
|       |   `-- FactList.vue
|       |-- views/          # Routable page components for this feature
|       |   |-- EntityDetailView.vue
|       |   `-- EntitySearchView.vue
|       |-- store.ts        # Pinia store for graph feature state
|       `-- routes.ts       # Routes specific to the graph feature
|
|-- router/
|   `-- index.ts            # Main router configuration, combines feature routes
|
|-- stores/
|   `-- index.ts            # Pinia setup and main store registration
|
|-- types/                  # Global TypeScript types and interfaces
|   `-- api.ts
|
|-- App.vue                 # Main application component (often contains the router-view)
`-- main.ts                 # App entry point (initializes Vue, router, Pinia)
```

---

## Explanation of Key Directories

- 📁 **`features/`**: This is the heart of the architecture. Instead of grouping files by type (all components together, all views together), you group them by **business functionality**. A feature like `graph` contains everything it needs to function independently: its own components, routable views, state management (`store.ts`), and routes.

- 📁 **`components/`**: This directory is for **truly global and reusable components** that are not tied to any specific feature. Think of UI kits (`AppButton.vue`) or application layout components (`MainLayout.vue`).

- 📁 **`router/`**: This handles all routing logic. The main `index.ts` file is responsible for creating the router instance and, most importantly, **importing and consolidating the route definitions from each feature module** in `features/*/routes.ts`.

- 📁 **`stores/`**: This is for your state management using **Pinia** (the official state management library for Vue). Each feature will have its own store file (e.g., `features/graph/store.ts`), making your state modular and easy to manage.

- 📁 **`api/`**: This layer is responsible for all communication with your FastAPI backend. It abstracts away the HTTP logic so your components and stores remain clean.

---

## Bootstrapping Your SPA (`main.ts` & Routing)

You asked specifically about bootstrapping. This happens in two main places: `main.ts` and `router/index.ts`.

#### 1\. Configure `main.ts` (The Entry Point)

Your `main.ts` should be lean. Its job is to create the Vue app instance and "plug in" your core modules like the router and state management.

**`apps/web/src/main.ts`**

```typescript
import { createApp } from "vue";
import { createPinia } from "pinia"; // Import Pinia
import router from "./router"; // Import the router

import App from "./App.vue";
import "./assets/styles/main.css";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia); // Use Pinia for state management
app.use(router); // Use the router

app.mount("#app");
```

#### 2\. Set Up Modular Routing

To keep your routing clean, each feature defines its own routes. The main router file then combines them.

**First, define routes for a feature:**
**`apps/web/src/features/graph/routes.ts`**

```typescript
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
```

**Next, combine feature routes in the main router:**
**`apps/web/src/router/index.ts`**

```typescript
import { createRouter, createWebHistory } from "vue-router";
import { graphRoutes } from "@/features/graph/routes"; // Import feature routes

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "Home",
      // Example of a simple home page component
      component: () => import("@/components/layout/MainLayout.vue"),
    },
    // Spread in the routes from your features
    ...graphRoutes,
    // ... add routes from other features here
  ],
});

export default router;
```

---

## State Management with Pinia

Pinia stores are perfect for this modular approach. You can create a store for each feature to manage its specific state.

**`apps/web/src/features/graph/store.ts`**

```typescript
import { defineStore } from "pinia";
import * as graphApi from "@/api/graphApi"; // Import your API functions
import type { Entity } from "@/types/api"; // Import your types

interface GraphState {
  entities: Entity[];
  isLoading: boolean;
  error: string | null;
}

// 'useGraphStore' is the hook you'll use in your components
export const useGraphStore = defineStore("graph", {
  state: (): GraphState => ({
    entities: [],
    isLoading: false,
    error: null,
  }),
  actions: {
    async searchEntities(query: string) {
      this.isLoading = true;
      this.error = null;
      try {
        // Call the API layer to fetch data
        const response = await graphApi.findEntityByIdentifier({
          type: "email",
          value: query,
        });
        this.entities = [response.entity]; // Adjust based on your API response
      } catch (err) {
        this.error = "Failed to fetch entities.";
      } finally {
        this.isLoading = false;
      }
    },
  },
});
```

---

## API Layer

Create a dedicated file for your API client setup and another for your feature-specific API calls. This separates concerns beautifully.

**`apps/web/src/api/index.ts`** (Example using `fetch`)

```typescript
const BASE_URL = "http://localhost:8000/api/v1"; // Or from .env

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;

  const defaultOptions: RequestInit = {
    headers: {
      "Content-Type": "application/json",
      // Add Authorization header if needed
    },
    ...options,
  };

  const response = await fetch(url, defaultOptions);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export default request;
```

**`apps/web/src/api/graphApi.ts`**

```typescript
import request from "./index";
import type { GetEntityResponse } from "@/types/api"; // Define your response types

interface FindParams {
  type: string;
  value: string;
}

export const findEntityByIdentifier = (
  params: FindParams
): Promise<GetEntityResponse> => {
  return request(
    `/graph/entities/lookup?type=${params.type}&value=${params.value}`
  );
};

// Add other functions like assimilateKnowledge here
```

---

## Next Steps 🚀

1.  **Install Dependencies**: Add `vue-router` and `pinia` to your `apps/web/package.json`.
    ```bash
    pnpm --filter web add vue-router pinia
    ```
2.  **Refactor**: Reorganize your `src` directory according to the structure above.
3.  **Implement**: Start by creating your router setup and your first feature module, `graph`. Create the `routes.ts` and a placeholder `EntitySearchView.vue`.
4.  **Connect**: Build out the API layer to start fetching data from your FastAPI backend.

This architecture will provide a solid, scalable foundation for your Vue.js application, making it a pleasure to work with as it evolves.
