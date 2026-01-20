---
title: Deployment
description: Deploy Nous to production
---

> **Just getting started?** See the [Installation Guide](/getting-started/installation/) for local development setup.

This guide covers deploying Nous to a production environment using Docker Compose.

## Deployment Modes

Nous supports two deployment modes:

| Mode | Use Case |
|------|----------|
| **Standalone** | Fresh servers — includes a bundled Caddy reverse proxy with automatic HTTPS |
| **BYO Reverse Proxy** | Servers with existing Caddy, Nginx, or Traefik — core services only |

## Prerequisites

- A server with Docker and Docker Compose installed
- A domain name (for HTTPS in standalone mode)
- A Google API key for embeddings

## Configuration

### 1. Clone the Repository

```bash
git clone https://github.com/jwandekoken/nous.git
cd nous
```

### 2. Create Your Environment File

```bash
cp .env.example .env
```

### 3. Configure Environment Variables

Edit `.env` with your production values:

```bash
# Required — generate with: openssl rand -hex 32
SECRET_KEY=your-secret-key-here

# Required for embeddings and fact extraction
GOOGLE_API_KEY=your-google-api-key

# Database credentials (change from defaults)
POSTGRES_PASSWORD=your-secure-password

# For standalone mode with HTTPS
DOMAIN=yourdomain.com
```

## Option A: Standalone Deployment

Use this if you don't have an existing reverse proxy. Caddy will handle SSL certificates automatically via Let's Encrypt.

### Start All Services

```bash
docker compose -f docker-compose.prod.yml --profile with-proxy up -d --build
```

Your application will be available at:
- `http://localhost` (if no domain configured)
- `https://yourdomain.com` (if `DOMAIN` is set)

## Option B: BYO Reverse Proxy

Use this if you already have a reverse proxy (Caddy, Nginx, Traefik) running on your server.

### Start Core Services

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

This starts the databases, API, and web frontend — but no reverse proxy.

### Connect Your Reverse Proxy

Your reverse proxy needs to connect to the `nous-net` Docker network to reach the internal services.

**Step 1:** Add the network to your reverse proxy's `docker-compose.yml`:

```yaml
networks:
  nous_nous-net:
    external: true

services:
  caddy:  # or nginx, traefik, etc.
    networks:
      - your-existing-network
      - nous_nous-net
```

**Step 2:** Add routing rules. Example for Caddy:

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

**Step 3:** Reload your reverse proxy:

```bash
docker exec your-caddy-container caddy reload --config /etc/caddy/Caddyfile
```

## Service Architecture

| Service | Container | Port (Internal) | Description |
|---------|-----------|-----------------|-------------|
| db | postgres_age | 5432 | PostgreSQL with Apache AGE (graph storage) |
| qdrant | qdrant | 6333 | Vector database (semantic search) |
| api | nous_api | 8000 | FastAPI backend |
| web | nous_web | 80 | Vue.js static frontend |
| reverse-proxy | nous_proxy | 80, 443 | Caddy (standalone mode only) |

## Managing Your Deployment

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f api
```

### Stop Services

```bash
docker compose -f docker-compose.prod.yml down
```

### Update to Latest Version

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `docker compose -f docker-compose.prod.yml up -d --build` | Start core services (BYO proxy) |
| `docker compose -f docker-compose.prod.yml --profile with-proxy up -d --build` | Start with bundled Caddy |
| `docker compose -f docker-compose.prod.yml down` | Stop all services |
| `docker compose -f docker-compose.prod.yml logs -f` | View logs |
| `docker compose -f docker-compose.prod.yml ps` | Check service status |

## Troubleshooting

### Containers Won't Start

1. Check logs: `docker compose -f docker-compose.prod.yml logs`
2. Verify `.env` file exists and has required variables
3. Ensure ports 80/443 aren't in use (standalone mode)

### Database Connection Issues

1. Check database health: `docker compose -f docker-compose.prod.yml ps`
2. View database logs: `docker compose -f docker-compose.prod.yml logs db`
3. Verify `POSTGRES_PASSWORD` matches in your `.env`

### SSL Certificate Issues (Standalone)

1. Ensure your domain's DNS points to your server
2. Check Caddy logs: `docker compose -f docker-compose.prod.yml logs reverse-proxy`
3. Verify port 443 is accessible from the internet

### API Returns 502 Bad Gateway

1. Check if the API container is running: `docker compose -f docker-compose.prod.yml ps api`
2. View API logs for errors: `docker compose -f docker-compose.prod.yml logs api`
3. Ensure database migrations have run successfully
