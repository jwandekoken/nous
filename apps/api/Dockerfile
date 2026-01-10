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
COPY entrypoint.sh ./

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

# Copy and make entrypoint executable
COPY --from=builder /app/entrypoint.sh ./
RUN chmod +x entrypoint.sh

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

# Run entrypoint (handles migrations + starts app)
CMD ["./entrypoint.sh"]
