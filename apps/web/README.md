# Nous Web App

The frontend application for the Nous AI Agent Memory System, built with **Vue 3**, **TypeScript**, and **Vite**.

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

## Project Structure

```plaintext
apps/web/src/
├── assets/               # Static assets
├── components/           # UI Components (Shadcn Vue)
│   └── ui/               # Base UI components (Buttons, Inputs, etc.)
├── composables/          # Shared Vue composables (hooks)
├── lib/                  # Utility functions (cn, clsx, etc.)
├── pages/                # Route views/pages
├── router/               # Vue Router configuration
├── services/             # API clients (mirrors API features)
│   ├── auth/
│   ├── graph/
│   └── ...
├── stores/               # Pinia stores
├── types/                # TypeScript type definitions
├── App.vue               # Root component
└── main.ts               # Application entry point
```

## Development

This project is part of a monorepo. For instructions on how to run the application, please refer to the [root README](../../README.md).

### Running the App

You can run the web app from the root of the monorepo:

```bash
# Run both API and Web
pnpm turbo dev

# Run only the Web app
pnpm turbo dev --filter=web
```

The application will be available at `http://localhost:5173`.

### Linting

```bash
pnpm turbo lint --filter=web
```

## Architecture

### Services Pattern

We use a **Service Layer** pattern to handle API communication. The `services/` directory is organized by feature, mirroring the backend API structure. Each service is responsible for:

- Making HTTP requests (using a configured Axios/Fetch instance).
- Typing the responses.
- Handling feature-specific logic.

### Component System

The UI is built using **Tailwind CSS** and **Shadcn Vue** for accessible, customizable components. Components are defined in `components/ui` and can be customized directly.

### Graph Visualization

The core feature of this application is the knowledge graph visualization, powered by **Cytoscape.js**. This allows users to interactively explore the nodes and edges stored in the PostgreSQL AGE database.
