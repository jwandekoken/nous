# Nous Web - The Visualization Dashboard

The frontend application for the Nous AI Agent Memory System, built with **Vue 3**, **TypeScript**, and **Vite**. It provides a visual interface to explore the Knowledge Graph and manage entities.

For setup and running instructions, please see the [Root README](../../README.md).

---

## Tech Stack

- **Framework**: [Vue 3](https://vuejs.org/) (Script Setup)
- **Build Tool**: [Vite](https://vitejs.dev/)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **State Management**: [Pinia](https://pinia.vuejs.org/)
- **Routing**: [Vue Router](https://router.vuejs.org/)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/)
- **UI Components**: [Shadcn Vue](https://www.shadcn-vue.com/)
- **Graph Visualization**: [Cytoscape.js](https://js.cytoscape.org/)
- **Utilities**: [VueUse](https://vueuse.org/)

---

## Project Structure

```plaintext
apps/web/src/
├── assets/               # Static assets
├── components/           # UI Components
│   ├── layout/           # App shell, Navigation
│   └── ui/               # Base UI components (Buttons, Inputs - Shadcn)
├── lib/                  # Utility functions
├── pages/                # Route views/pages
├── router/               # Vue Router configuration
├── services/             # API CLIENTS (Service Layer)
│   ├── auth/
│   ├── graph/
│   └── ...
├── stores/               # Pinia stores
├── types/                # TypeScript definitions
├── App.vue               # Root component
└── main.ts               # Application entry point
```

---

## Development

### Running the App

You can run the web app from the root of the monorepo:

```bash
# Run both API and Web (Recommended)
pnpm turbo dev

# Run only the Web app
pnpm turbo dev --filter=web
```

The application will be available at `http://localhost:5173`.

### Linting

```bash
pnpm turbo lint --filter=web
```

---

## Architecture

### Service Layer Pattern

We use a **Service Layer** pattern in `services/` to handle all API communication. This layer:

1.  Mirrors the backend API structure (e.g., `services/graph` matches `api/features/graph`).
2.  Handles HTTP requests and response typing.
3.  Keeps components clean of API logic.

### Graph Visualization

The core feature is the **interactive graph explorer**, powered by **Cytoscape.js**. It renders the entities and relationships stored in the PostgreSQL AGE database, allowing users to visually inspect the agent's memory.
