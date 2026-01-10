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

### How to Start the Databases

We use Docker Compose to run the databases:

- **PostgreSQL** with Apache AGE extension (graph database)
- **Qdrant** (vector database for embeddings)

```bash
docker compose up -d
```

| Service    | Port | Description                 |
| ---------- | ---- | --------------------------- |
| PostgreSQL | 5432 | Relational + graph database |
| Qdrant     | 6333 | Vector database (HTTP API)  |
| Qdrant     | 6334 | Vector database (gRPC API)  |

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

This command is the most common command you'll use. Turborepo finds _all_ projects with a `dev` script and runs them in parallel.

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

You've already used this! The `--filter` flag lets you run tasks on a single project or a subset of projects.

```bash
# Run `build` only on the `web` app
pnpm turbo build --filter=web
```

### 🏎️ Parallel Execution

When you run a command like `pnpm turbo dev` or `pnpm turbo lint`, Turborepo reads your `turbo.json` and understands that these tasks can be run in parallel, maximizing your CPU usage and finishing faster.

## 4. Production Deployment

For production, we provide a Docker Compose configuration with **two deployment modes**:

1. **Standalone** - Includes a bundled Caddy reverse proxy (for fresh servers)
2. **BYO Reverse Proxy** - Core services only (for servers with existing Caddy/Nginx)

### Setup

1. **Create your production environment file:**

   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** with your production values:

   ```bash
   # Required - generate with: openssl rand -hex 32
   SECRET_KEY=your-secret-key-here

   # Required for embeddings
   GOOGLE_API_KEY=your-google-api-key

   # Database credentials (change from defaults for production)
   POSTGRES_PASSWORD=your-secure-password

   # For standalone mode with HTTPS (optional):
   DOMAIN=yourdomain.com
   ```

### Option A: Standalone (with bundled reverse proxy)

Use this if you don't have an existing reverse proxy. Caddy will handle SSL automatically.

```bash
# Build and start all services including reverse proxy
docker compose -f docker-compose.prod.yml --profile with-proxy up -d --build

# The app will be available at http://localhost (or https://yourdomain.com if DOMAIN is set)
```

### Option B: BYO Reverse Proxy

Use this if you already have Caddy, Nginx, or Traefik running on your server.

```bash
# Build and start core services only (no reverse proxy)
docker compose -f docker-compose.prod.yml up -d --build
```

Then connect your existing reverse proxy to the `nous-net` network. See [Connecting Your Reverse Proxy](#connecting-your-reverse-proxy) below.

### Managing Services

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f

# View logs for a specific service
docker compose -f docker-compose.prod.yml logs -f api

# Stop all services
docker compose -f docker-compose.prod.yml down
```

### Production Architecture

| Service       | Container    | Description                                     |
| ------------- | ------------ | ----------------------------------------------- |
| db            | postgres_age | PostgreSQL with Apache AGE                      |
| qdrant        | qdrant       | Vector database                                 |
| api           | nous_api     | FastAPI backend (port 8000 internal)            |
| web           | nous_web     | Vue.js SPA static server (port 80 internal)     |
| reverse-proxy | nous_proxy   | Caddy reverse proxy (optional, standalone only) |

### Connecting Your Reverse Proxy

If using BYO mode, your reverse proxy needs to connect to the `nous-net` network to reach the `nous_api` and `nous_web` containers.

**Step 1:** Add the network to your reverse proxy's `docker-compose.yml`:

```yaml
networks:
  nous_nous-net:
    external: true

services:
  caddy: # or nginx, traefik, etc.
    networks:
      - your-existing-network
      - nous_nous-net
```

**Step 2:** Add routing rules to your reverse proxy config. Example for Caddy:

```caddyfile
nous.yourdomain.com {
    handle /api/* {
        reverse_proxy nous_api:8000
    }
    handle {
        reverse_proxy nous_web:80
    }
}
```

See `deploy/examples/caddy-external.example` for a complete example with setup instructions.

**Step 3:** Reload your reverse proxy:

```bash
docker exec your-caddy-container caddy reload --config /etc/caddy/Caddyfile
```

### Quick Reference

| Command                                                                        | Description                             |
| ------------------------------------------------------------------------------ | --------------------------------------- |
| `docker compose up -d`                                                         | Start databases (development)           |
| `docker compose down`                                                          | Stop databases                          |
| `pnpm turbo dev`                                                               | Start API + Web locally with hot-reload |
| `docker compose -f docker-compose.prod.yml up -d --build`                      | Start core services (BYO reverse proxy) |
| `docker compose -f docker-compose.prod.yml --profile with-proxy up -d --build` | Start full stack with bundled Caddy     |
| `docker compose -f docker-compose.prod.yml down`                               | Stop all services                       |

## 5. High-Level Directory Structure

```plaintext
nous/
├── apps/
│   ├── api/               # FastAPI (Python) backend
│   │   ├── Dockerfile     # Production container image
│   │   └── ...
│   └── web/               # Vue.js (TypeScript) frontend
│       ├── Dockerfile     # Production container image
│       ├── Caddyfile      # Internal SPA static file server config
│       └── ...
├── deploy/
│   ├── caddy/
│   │   └── Caddyfile      # Bundled reverse proxy config (standalone mode)
│   └── examples/
│       └── caddy-external.example  # Example for BYO reverse proxy setup
├── docker/
│   └── postgres/          # Custom PostgreSQL + AGE image
├── docker-compose.yml     # Development: databases only
├── docker-compose.prod.yml # Production: full stack (with optional reverse proxy)
├── .env.example           # Template for production environment variables
├── package.json           # Root Node.js dependencies (contains `turbo`)
├── pnpm-workspace.yaml    # Defines the `apps/*` as pnpm workspaces
└── turbo.json             # Defines the monorepo task pipeline
```

## 6. Troubleshooting

### Common Issues

**1. Ports already in use**
If you see an error like `Bind for 0.0.0.0:5432 failed: port is already allocated`, it means another service (like a local Postgres instance) is using that port.

- **Solution**: Stop the local service or change the port mapping in `docker-compose.yml` (e.g., `"5433:5432"`).

**2. Database connection failed**
If the API fails to connect to the database:

- Ensure the database container is healthy: `docker compose ps`
- Check logs: `docker compose logs db`
- Verify environment variables in `.env` (for production) or `apps/api/.env` (for dev).

**3. "File not found" in Docker build**
If the build fails because it can't find a file:

- Check `.dockerignore` to make sure you aren't excluding necessary files.
- Ensure you are running the build from the root `nous/` directory.

**4. Hot reload not working (Development)**

- Ensure you are running `pnpm turbo dev`.
- Check if your file watcher limit is reached (Linux/macOS).
