# Nous Monorepo

Welcome to the `nous` project monorepo. This repository contains all the code for the Nous AI Agent Memory System, including the FastAPI backend (`api`) and the Vue.js frontend (`web`).

This project is managed as a **polyglot (Python + TypeScript) monorepo** using **pnpm Workspaces** and **Turborepo**.

- **`pnpm`** manages the JavaScript **dependencies** and workspaces.
- **`Turborepo`** orchestrates tasks (like `dev`, `test`, `lint`) across all projects.
- **`uv`** manages the Python dependencies and virtual environment for the `api`.

## Prerequisites

Before you begin, ensure you have the following tools installed:

1.  **Node.js**: Version `24.11.0` or higher is required. We recommend using [nvm](https://github.com/nvm-sh/nvm).
2.  **pnpm**: The JavaScript package manager. [Installation guide](https://pnpm.io/installation).
3.  **uv**: The Python package manager. [Installation guide](https://docs.astral.sh/uv/getting-started/installation/).

## 1. Initial Setup

To get your environment ready, run these commands from the root (`nous/`) directory:

1.  **Install Node.js Dependencies:**
    This command installs all Node.js dependencies for the entire monorepo, including `turbo` at the root and all dependencies for each application inside `apps/` (like `vite` for `web`). It also links the workspace packages together.

    ```bash
    pnpm install
    ```

2.  **Set up Python Environment:**
    You only need to do this once for the `api` project.

    ```bash
    # 1. Navigate to the api directory
    cd apps/api

    # 2. Create a virtual environment
    uv venv

    # 3. Install all Python dependencies
    uv sync

    # 4. Go back to the root
    cd ../..
    ```

3.  **Set up Environment Variables:**
    The API requires a `.env` file for its configuration.

    ```bash
    # From the root directory:
    cp apps/api/.env.example apps/api/.env

    # Now, edit apps/api/.env with your database credentials.
    ```

## 2. Development Workflow

All commands should be run from the **root of the monorepo**.

### How to Start the Database

We use Docker Compose to run the PostgreSQL database with Apache AGE and pgvector extensions.

```bash
docker compose up -d
```

The database will be available on port `5432`.

> **Note:** In the future, we will package both the api and the web also in the docker-compose setup (we wont do it now).

### How to Start the API

This command uses Turborepo to find the `api` project and run its `dev` script.

```bash
pnpm turbo dev --filter=api
```

Your FastAPI server will be running on `http://localhost:8000`.

---

### How to Start the Web-App

This command uses Turborepo to find the `web` project and run its `dev` script.

```bash
pnpm turbo dev --filter=web
```

Your Vue.js app will be running on `http://localhost:5173` (or the next available port).

---

### How to Start Both (API + Web)

This is the most common command you'll use. Turborepo finds _all_ projects with a `dev` script and runs them in parallel.

```bash
pnpm turbo dev
```

---

### How to Run Tests

This command runs the `test` script in all projects.

```bash
pnpm turbo test
```

> **Note:** The `apps/web` project currently has a placeholder test script. This command will primarily run the **Python tests** for the `api`.

---

### How to Run Linting

This command runs the `lint` script in all projects (`ruff` for the API, `eslint` for the web app).

```bash
pnpm turbo lint
```

## 3. What Else Can I Do with Turborepo?

Turborepo is more than just a task runner; it's a build system that makes your monorepo fast and efficient.

### ⚡️ Caching (The "Turbo")

This is Turborepo's killer feature.

- **What it does:** Turborepo caches the output and logs of your tasks (like `test`, `lint`, and `build`).
- **Why it's great:** If you run `pnpm turbo test`, and then run it again without changing any files in `apps/api`, Turborepo will **skip** running the tests and show you the cached result instantly. This saves a massive amount of time, especially in CI/CD pipelines.

### 🎯 Filtering

You've already used this\! The `--filter` flag lets you run tasks on a single project or a subset of projects.

```bash
# Run `build` only on the `web` app
pnpm turbo build --filter=web
```

### 🏎️ Parallel Execution

When you run a command like `pnpm turbo dev` or `pnpm turbo lint`, Turborepo reads your `turbo.json` and understands that these tasks can be run in parallel, maximizing your CPU usage and finishing faster.

## 4. High-Level Directory Structure

```plaintext
nous/
├── apps/
│   ├── api/          # FastAPI (Python) backend
│   └── web/          # Vue.js (TypeScript) frontend
├── package.json      # Root Node.js dependencies (contains `turbo`)
├── pnpm-workspace.yaml # Defines the `apps/*` as pnpm workspaces
└── turbo.json        # Defines the monorepo task pipeline
```
