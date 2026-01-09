# Docker Setup Plan

This document outlines the plan to containerize the full Nous application stack with separate configurations for development and production environments.

## Overview

### Goals

1. **Development**: Run only databases in Docker, with API and Web running locally via `pnpm turbo dev`
2. **Production**: Run the entire stack (databases + API + Web) in Docker

### Files to Create

| File                      | Purpose                                  |
| ------------------------- | ---------------------------------------- |
| `docker-compose.yml`      | Development: databases only              |
| `docker-compose.prod.yml` | Production: full stack                   |
| `apps/api/Dockerfile`     | API container image                      |
| `apps/web/Dockerfile`     | Web container image                      |
| `apps/web/Caddyfile`      | Caddy config for SPA routing + API proxy |

---

## 1. Development Setup (`docker-compose.yml`)

The existing `docker-compose.yml` will be used for development. It only runs the databases, allowing developers to run the API and Web app locally with hot-reload.

### Workflow

```bash
# Start databases
docker compose up -d

# Start API and Web with hot-reload
pnpm turbo dev
```

### File: `docker-compose.yml`

```yaml
# =============================================================================
# Development Docker Compose - Databases Only
# =============================================================================
# Usage: docker compose up -d
# Then run: pnpm turbo dev
# =============================================================================

services:
  db:
    build:
      context: ./docker/postgres
    container_name: postgres_age
    restart: unless-stopped
    command: >
      postgres
      -c shared_preload_libraries=age
    environment:
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=supersecretpassword
      - POSTGRES_DB=multimodel_db
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - nous-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin -d multimodel_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.16.2
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant-data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__ENABLE_TELEMETRY=false
      - QDRANT__STORAGE__OPTIMIZERS__DELETED_THRESHOLD=0.2
    ulimits:
      nofile:
        soft: 65535
        hard: 65535
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 1G
    networks:
      - nous-net
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:6333/readiness"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres-data:
    driver: local
  qdrant-data:
    driver: local

networks:
  nous-net:
    driver: bridge
```

---

## 2. Production Setup (`docker-compose.prod.yml`)

A separate compose file for production that includes the API and Web services.

### Workflow

```bash
# Build and start everything
docker compose -f docker-compose.prod.yml up -d --build

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop everything
docker compose -f docker-compose.prod.yml down
```

### File: `docker-compose.prod.yml`

```yaml
# =============================================================================
# Production Docker Compose - Full Stack
# =============================================================================
# Usage: docker compose -f docker-compose.prod.yml up -d --build
# =============================================================================

services:
  # ---------------------------------------------------------------------------
  # Databases
  # ---------------------------------------------------------------------------
  db:
    build:
      context: ./docker/postgres
    container_name: postgres_age
    restart: unless-stopped
    command: >
      postgres
      -c shared_preload_libraries=age
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-admin}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-supersecretpassword}
      - POSTGRES_DB=${POSTGRES_DB:-multimodel_db}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - nous-net
    healthcheck:
      test:
        [
          "CMD-SHELL",
          "pg_isready -U ${POSTGRES_USER:-admin} -d ${POSTGRES_DB:-multimodel_db}",
        ]
      interval: 5s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.16.2
    container_name: qdrant
    restart: unless-stopped
    volumes:
      - qdrant-data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__ENABLE_TELEMETRY=false
      - QDRANT__STORAGE__OPTIMIZERS__DELETED_THRESHOLD=0.2
    ulimits:
      nofile:
        soft: 65535
        hard: 65535
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 1G
    networks:
      - nous-net
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:6333/readiness"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ---------------------------------------------------------------------------
  # API - FastAPI Backend
  # ---------------------------------------------------------------------------
  api:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    container_name: nous_api
    restart: unless-stopped
    environment:
      # Database (PostgreSQL with AGE)
      - POSTGRES_HOST=db
      - POSTGRES_PORT=5432
      - POSTGRES_USER=${POSTGRES_USER:-admin}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-supersecretpassword}
      - POSTGRES_DB=${POSTGRES_DB:-multimodel_db}
      - AGE_GRAPH_NAME=${AGE_GRAPH_NAME:-nous}
      # Qdrant
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      # Security (MUST be set in production)
      - SECRET_KEY=${SECRET_KEY:?SECRET_KEY is required}
      # Google AI (required for embeddings)
      - GOOGLE_API_KEY=${GOOGLE_API_KEY:?GOOGLE_API_KEY is required}
      # Application
      - DEBUG=false
    depends_on:
      db:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    networks:
      - nous-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ---------------------------------------------------------------------------
  # Web - Vue.js Frontend (served via Caddy)
  # ---------------------------------------------------------------------------
  web:
    build:
      context: ./apps/web
      dockerfile: Dockerfile
    container_name: nous_web
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      api:
        condition: service_healthy
    networks:
      - nous-net

volumes:
  postgres-data:
    driver: local
  qdrant-data:
    driver: local

networks:
  nous-net:
    driver: bridge
```

---

## 3. API Dockerfile (`apps/api/Dockerfile`)

Multi-stage build using the official `uv` image for fast dependency installation.

```dockerfile
# =============================================================================
# Nous API - FastAPI with uv
# =============================================================================
# Build: docker build -t nous-api .
# Run:   docker run -p 8000:8000 nous-api
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies without the project itself
# --frozen: fail if lockfile is out of date
# --no-install-project: don't install the project, just dependencies
# --no-dev: skip dev dependencies
RUN uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY app/ ./app/
COPY alembic.ini ./
COPY migrations/ ./migrations/

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application files
COPY --from=builder /app/app ./app
COPY --from=builder /app/alembic.ini ./
COPY --from=builder /app/migrations ./migrations

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Web Dockerfile (`apps/web/Dockerfile`)

Multi-stage build that compiles the Vue app and serves it via Caddy.

```dockerfile
# =============================================================================
# Nous Web - Vue 3 + Vite (Production Build)
# =============================================================================
# Build: docker build -t nous-web .
# Run:   docker run -p 80:80 nous-web
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Build the Vue application
# -----------------------------------------------------------------------------
FROM node:24-alpine AS builder

# Enable corepack for pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy dependency files first for better caching
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build the application
RUN pnpm build

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Serve with Caddy
# -----------------------------------------------------------------------------
FROM caddy:alpine AS runtime

# Copy Caddyfile
COPY Caddyfile /etc/caddy/Caddyfile

# Copy built assets from builder
COPY --from=builder /app/dist /srv

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

# Caddy runs automatically via the base image entrypoint
```

---

## 5. Caddy Configuration (`apps/web/Caddyfile`)

Handles SPA routing and proxies API requests to the backend. Caddy provides automatic compression, security headers, and HTTP/2 by default.

```caddyfile
# =============================================================================
# Nous Web - Caddyfile
# =============================================================================
# For local/Docker: serves on :80
# For production with domain: replace :80 with yourdomain.com for auto-HTTPS
# =============================================================================

:80 {
    # Serve static files from /srv
    root * /srv

    # Enable gzip and brotli compression (automatic)
    encode gzip

    # Proxy API requests to the backend
    handle /api/* {
        reverse_proxy api:8000
    }

    # Health endpoint for container health checks
    handle /health {
        respond "OK" 200
    }

    # SPA fallback - serve index.html for all other routes
    handle {
        try_files {path} /index.html
        file_server
    }
}
```

### Caddy Advantages (vs Nginx)

- **Simpler config**: ~20 lines vs ~40 lines
- **Automatic HTTPS**: Change `:80` to `yourdomain.com` for auto Let's Encrypt
- **Modern defaults**: HTTP/2, security headers, compression all automatic
- **No reload needed**: Config changes apply automatically

---

## 6. Environment Variables

There are **two separate `.env` files** for different purposes:

| File            | Used By                     | Purpose                                   |
| --------------- | --------------------------- | ----------------------------------------- |
| `apps/api/.env` | FastAPI (pydantic-settings) | Local development with `pnpm turbo dev`   |
| Root `.env`     | Docker Compose              | Production with `docker-compose.prod.yml` |

### Why Two Files?

- **Development**: When running locally, the API reads `apps/api/.env` directly via pydantic-settings
- **Production**: Docker Compose reads the root `.env` and injects values into container environment variables

### Root `.env.example` (for Production)

Create `.env.example` in the root directory as a template:

```bash
# =============================================================================
# Production Environment Variables (for docker-compose.prod.yml)
# =============================================================================
# Copy this file to .env and fill in the values:
#   cp .env.example .env
# =============================================================================

# -----------------------------------------------------------------------------
# Database (PostgreSQL with AGE)
# -----------------------------------------------------------------------------
POSTGRES_USER=admin
POSTGRES_PASSWORD=<strong-password-here>
POSTGRES_DB=multimodel_db
AGE_GRAPH_NAME=nous

# -----------------------------------------------------------------------------
# Security (REQUIRED - generate with: openssl rand -hex 32)
# -----------------------------------------------------------------------------
SECRET_KEY=<your-secret-key-here>

# -----------------------------------------------------------------------------
# Google AI (required for embeddings)
# -----------------------------------------------------------------------------
GOOGLE_API_KEY=<your-google-api-key>

# -----------------------------------------------------------------------------
# CORS (optional - defaults work for standard setup)
# -----------------------------------------------------------------------------
# ALLOWED_ORIGINS=http://localhost,https://yourdomain.com
```

### Variables Set by Docker Compose (NOT in `.env`)

These are hardcoded in `docker-compose.prod.yml` because they refer to **internal Docker network hostnames**:

| Variable        | Value    | Why                                  |
| --------------- | -------- | ------------------------------------ |
| `POSTGRES_HOST` | `db`     | Docker service name, not `localhost` |
| `POSTGRES_PORT` | `5432`   | Standard port                        |
| `QDRANT_HOST`   | `qdrant` | Docker service name                  |
| `QDRANT_PORT`   | `6333`   | Standard port                        |

> **Note**: The root `.env` file is **only used in production** (by Docker Compose). For local development, you only need `apps/api/.env`.

---

## 7. Implementation Checklist

### Phase 1: Update Development Setup

- [x] Update `docker-compose.yml` with health checks and renamed network
- [x] Test that `docker compose up -d` + `pnpm turbo dev` works

### Phase 2: Create Dockerfiles

- [x] Create `apps/api/Dockerfile`
- [x] Create `apps/web/Dockerfile`
- [x] Create `apps/web/Caddyfile`
- [x] Add `.dockerignore` files to both apps

### Phase 3: Create Production Compose

- [x] Create `docker-compose.prod.yml`
- [x] Create root `.env.example` (template for production secrets)
- [ ] Test full stack with `docker compose -f docker-compose.prod.yml up -d --build`

### Phase 4: Documentation

- [x] Update root `README.md` with production deployment instructions
- [x] Add troubleshooting section

---

## 8. Additional Files

### `apps/api/.dockerignore`

```
__pycache__
*.pyc
*.pyo
.venv
.env
.git
.gitignore
.pytest_cache
.ruff_cache
*.egg-info
dist
build
tests
docs
*.md
```

### `apps/web/.dockerignore`

```
node_modules
dist
.git
.gitignore
*.md
.env*
.vscode
```

---

## 9. Quick Reference

| Command                                                   | Description                             |
| --------------------------------------------------------- | --------------------------------------- |
| `docker compose up -d`                                    | Start databases (development)           |
| `docker compose down`                                     | Stop databases                          |
| `pnpm turbo dev`                                          | Start API + Web locally with hot-reload |
| `docker compose -f docker-compose.prod.yml up -d --build` | Start full stack (production)           |
| `docker compose -f docker-compose.prod.yml down`          | Stop full stack                         |
| `docker compose -f docker-compose.prod.yml logs -f api`   | View API logs                           |
