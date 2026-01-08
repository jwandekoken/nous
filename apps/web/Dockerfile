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

