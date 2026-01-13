# Nous

**A Knowledge Graph Memory & Semantic Layer for AI Agents**

> "Commonly translated as 'mind' or 'intellect', the Greek word _nous_ is a key term in the philosophies of Plato, Aristotle and Plotinus."

---

## ⚠️ Project Status: Alpha (v0.1.0)

**Warning:** This software is currently in an **Alpha** state.

- **Stability:** APIs are subject to breaking changes without notice.
- **Recommendation:** This project is suitable for testing, development, and experimental use. It is **not yet recommended for mission-critical production environments**.

---

## Why Nous?

AI agents today suffer from two main limitations: **limited context windows** and **statelessness**. They often forget details from past interactions or cannot access a cohesive view of the world across different sessions.

**Nous** solves this by providing a dedicated Knowledge Graph Memory layer that combines:

1.  **Graph Database (Apache AGE):** To store structured relationships (entities, facts).
2.  **Vector Database (Qdrant):** To store semantic embeddings for fuzzy search and retrieval.

This allows agents to "remember" facts, understand relationships, and retrieve relevant context on demand.

---

## Core Concepts

Understanding these four concepts is key to using Nous:

1.  **Entity**: The central subject of memory (e.g., a person, a company, a topic). Each entity has a stable, unique ID.
2.  **Identifier**: The external handle used to find an entity (e.g., email `alice@example.com`, phone `+1234567890`).
3.  **Fact**: A discrete piece of knowledge associated with an entity (e.g., "Lives in Paris", "Works as Engineer").
4.  **Source**: The origin of a fact (e.g., a chat message, a document), providing provenance and traceability.

---

## API Overview

Nous exposes two primary operations for interacting with memory:

### 1. Assimilate (Write)

**Endpoint:** `POST /entities/assimilate`

Extracts facts from unstructured text and saves them to the graph.

- **Input:** Raw text content (e.g., "Alice moved to Berlin yesterday.") and an identifier.
- **Process:** The system extracts facts ("Location: Berlin") using an LLM and links them to the entity "Alice".

### 2. Lookup (Read)

**Endpoint:** `GET /entities/lookup`

Retrieves the structured memory of an entity.

- **Input:** An identifier (e.g., `email: alice@example.com`).
- **Output:** Returns the entity profile with all associated facts and their original sources.
- **Summary Mode:** `GET /entities/lookup/summary` generates a natural language summary of the entity's history, optimized for feeding back into an LLM context window.

---

## Getting Started

### Prerequisites

Ensure you have the following tools installed:

1.  **Node.js**: Version `24.11.0` or higher (we recommend [nvm](https://github.com/nvm-sh/nvm)).
2.  **pnpm**: The JavaScript package manager. [Installation guide](https://pnpm.io/installation).
3.  **uv**: The Python package manager. [Installation guide](https://docs.astral.sh/uv/getting-started/installation/).
4.  **Docker**: For running the databases.

### Installation

1.  **Clone and Install Dependencies:**
    Run this from the root `nous/` directory to install dependencies for both Python (API) and Node.js (Web/Tooling).

    ```bash
    pnpm install
    ```

2.  **Set up Python Environment (API):**

    ```bash
    cd apps/api
    uv venv
    uv sync
    cd ../..
    ```

3.  **Configure Environment Variables:**

    ```bash
    cp apps/api/.env.example apps/api/.env
    # Edit apps/api/.env with your API keys (e.g., GOOGLE_API_KEY) and DB credentials.
    ```

### Running the Project

1.  **Start the Databases:**
    Spin up PostgreSQL (Graph) and Qdrant (Vector).

    ```bash
    docker compose up -d
    ```

2.  **Run Migrations:**
    Initialize the database schema.

    ```bash
    cd apps/api
    uv run alembic upgrade head
    cd ../..
    ```

3.  **Start the Development Servers:**
    This runs both the API (`localhost:8000`) and the Web App (`localhost:5173`) in parallel.

    ```bash
    pnpm turbo dev
    ```

---

## Project Structure

Nous is a polyglot monorepo managed by **Turborepo**:

```plaintext
nous/
├── apps/
│   ├── api/               # FastAPI (Python) backend - The Core Memory System
│   └── web/               # Vue.js (TypeScript) frontend - Visualization Dashboard
├── deploy/                # Deployment configurations (Caddy, etc.)
├── docker/                # Custom Docker images (Postgres + AGE)
├── docker-compose.yml     # Dev infrastructure
├── package.json           # Root dependencies & scripts
└── pnpm-workspace.yaml    # Workspace definition
```

---

## Production Deployment

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

## Troubleshooting

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
