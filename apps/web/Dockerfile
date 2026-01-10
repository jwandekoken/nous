# =============================================================================
# Nous Web - Vue 3 + Vite (Production Build)
# =============================================================================
# Build context: monorepo root (for pnpm workspace support)
# Build: docker compose -f docker-compose.prod.yml build web
#
# This image serves the built Vue.js SPA on port 80 (internal only).
# An external reverse proxy handles SSL termination and API routing.
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Build the Vue application
# -----------------------------------------------------------------------------
FROM node:24-alpine AS builder

# Enable corepack for pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy workspace configuration files from monorepo root
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Copy the web app package.json for dependency resolution
COPY apps/web/package.json ./apps/web/

# Install dependencies (workspace-aware)
RUN pnpm install --frozen-lockfile --filter web...

# Copy web app source code
COPY apps/web/ ./apps/web/

# Set API URL for production build (relative path goes through reverse proxy)
ENV VITE_API_URL=/api/v1

# Build the application
RUN pnpm --filter web build

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Internal SPA Static File Server
# -----------------------------------------------------------------------------
# Serves static files on port 80 (internal). Caddy handles SPA routing
# (try_files fallback for Vue Router) and gzip compression.
# -----------------------------------------------------------------------------
FROM caddy:alpine AS runtime

# Copy Caddyfile (internal static server config)
COPY apps/web/Caddyfile /etc/caddy/Caddyfile

# Copy built assets from builder
COPY --from=builder /app/apps/web/dist /srv

# Expose internal port (no SSL - reverse proxy handles that)
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

# Caddy runs automatically via the base image entrypoint
