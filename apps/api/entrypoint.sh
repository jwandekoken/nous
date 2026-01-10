#!/bin/bash
# =============================================================================
# Nous API - Entrypoint Script
# =============================================================================
# This script runs on every container start:
#   1. Waits for the database to be ready
#   2. Runs database migrations (idempotent - safe to run every time)
#   3. Starts the FastAPI application
# =============================================================================

set -e

echo "==> Waiting for database to be ready..."

# Wait for PostgreSQL to be available (max 30 seconds)
for i in {1..30}; do
    if python -c "
import asyncio
import asyncpg
import os

async def check():
    try:
        conn = await asyncpg.connect(
            host=os.environ.get('POSTGRES_HOST', 'db'),
            port=int(os.environ.get('POSTGRES_PORT', '5432')),
            user=os.environ.get('POSTGRES_USER', 'admin'),
            password=os.environ.get('POSTGRES_PASSWORD', ''),
            database=os.environ.get('POSTGRES_DB', 'multimodel_db'),
        )
        await conn.close()
        return True
    except Exception:
        return False

exit(0 if asyncio.run(check()) else 1)
" 2>/dev/null; then
        echo "==> Database is ready!"
        break
    fi
    echo "    Waiting for database... ($i/30)"
    sleep 1
done

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
