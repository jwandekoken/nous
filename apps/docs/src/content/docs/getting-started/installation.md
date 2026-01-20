---
title: Installation
description: How to install and set up Nous for local development
---

> **Looking to deploy to production?** Skip to the [Deployment Guide](/getting-started/deployment/).

This guide will help you get Nous running locally for development and testing.

## Prerequisites

Before you begin, ensure you have the following tools installed:

| Tool | Version | Purpose |
|------|---------|---------|
| [Node.js](https://nodejs.org/) | 24.11.0+ | JavaScript runtime (we recommend [nvm](https://github.com/nvm-sh/nvm)) |
| [pnpm](https://pnpm.io/installation) | Latest | JavaScript package manager |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Latest | Python package manager |
| [Docker](https://docs.docker.com/get-docker/) | Latest | Container runtime for databases |

## Quick Start

### 1. Clone and Install Dependencies

```bash
git clone https://github.com/jwandekoken/nous.git
cd nous
pnpm install
```

### 2. Set Up the Python Environment

```bash
cd apps/api
uv venv
uv sync
cd ../..
```

### 3. Configure Environment Variables

```bash
cp apps/api/.env.example apps/api/.env
```

Edit `apps/api/.env` with your configuration:

```bash
# Required for fact extraction and embeddings
GOOGLE_API_KEY=your-google-api-key
```

### 4. Start the Databases

Nous requires two databases:
- **PostgreSQL + Apache AGE** — Graph storage for entities and relationships
- **Qdrant** — Vector storage for semantic search

```bash
docker compose up -d
```

### 5. Run Database Migrations

```bash
cd apps/api
uv run alembic upgrade head
cd ../..
```

### 6. Start the Development Servers

```bash
pnpm turbo dev
```

This starts both services:
- **API** at `http://localhost:8000`
- **Web Dashboard** at `http://localhost:5173`

## Verify Your Installation

Once everything is running, you can verify the installation:

**1. Check the health endpoint:**

```bash
curl http://localhost:8000/health
```

You should see: `{"status":"healthy"}`

**2. View the services:**
- **API Documentation**: http://localhost:8000/docs
- **Web Dashboard**: http://localhost:5173

**3. Next:** Follow the [Quick Start Guide](/getting-started/quickstart/) to set up authentication and start using the API.

## Troubleshooting

### Port Already in Use

If you see `port is already allocated`, another service is using the port (commonly PostgreSQL on 5432). Either stop that service or modify the port mapping in `docker-compose.yml` (e.g., change `"5432:5432"` to `"5433:5432"`).

### Database Connection Failed

1. Check that containers are running: `docker compose ps`
2. View database logs: `docker compose logs db`
3. Verify your `.env` configuration matches the database credentials

### Hot Reload Not Working

Ensure you're running `pnpm turbo dev` from the repository root. Also check if your system's file watcher limit is reached (common on Linux).

## Next Steps

Now that Nous is running locally, you can:
- Explore the API at http://localhost:8000/docs
- Visualize your knowledge graph in the Web Dashboard
- Read about [Deployment](/getting-started/deployment/) when you're ready for production
