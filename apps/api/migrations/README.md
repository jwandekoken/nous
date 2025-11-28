# Managing Database Migrations with Alembic

This project uses Alembic to manage database schema migrations. All migrations are located in the `migrations/versions` directory.

## How it Works

Alembic works by comparing the state of your SQLAlchemy models (e.g., in `app/features/auth/models.py`) against the current state of the database schema. When it detects differences, it can automatically generate a migration script to apply those changes.

## Key Files and Directories

- `env.py`: This is the main runtime configuration script for Alembic. It's where we programmatically define how to connect to our database and where Alembic should look for our SQLAlchemy models (`target_metadata`) to detect changes for autogeneration.

  > [!NOTE]
  > We have customized `env.py` to automatically create the PostgreSQL `age` extension (if it doesn't exist) whenever migrations are run in "online" mode. This ensures the extension is always available, even if you reset your migration files.

- `script.py.mako`: This is a Mako template file that Alembic uses to generate new migration files. You can edit this file to change the structure of the generated revision scripts.

- `versions/`: This directory contains all the migration scripts. Each file in this directory represents a sequential change to the database schema. These scripts contain two main functions: `upgrade()` to apply the changes and `downgrade()` to revert them.

## Common Commands

All commands should be run from the `apps/api` directory using `uv run`.

### Generating a New Migration

Whenever you make changes to your SQLAlchemy models (e.g., add a new table or a new column), you need to generate a migration script.

```bash
uv run alembic revision --autogenerate -m "A descriptive name for your migration"
```

This will create a new file in `migrations/versions/` containing the Python code to apply (`upgrade`) and revert (`downgrade`) your changes. **Always review the generated migration script** to ensure it's correct before applying it.

### Applying Migrations

To apply all pending migrations to your database, use the `upgrade` command. `head` refers to the latest migration.

```bash
uv run alembic upgrade head
```

You can also upgrade to a specific migration by providing its revision ID.

### Downgrading Migrations

To revert the last applied migration, you can use `downgrade`.

```bash
# Downgrade by one revision
uv run alembic downgrade -1
```

To revert all migrations, you can downgrade to `base`.

```bash
uv run alembic downgrade base
```

### Checking Migration Status

To see the current revision of the database and identify which migrations have not been applied, you can use these commands:

```bash
# Show the current revision
uv run alembic current

# Show the history of migrations
uv run alembic history
```

## Starting Migrations from Scratch

If you need to completely reset your migrations and start fresh (e.g., after major model changes or during development), follow these steps:

### Option 1: Complete Reset (Recommended for Development)

```bash
# 1. Remove all existing migration files
rm -f migrations/versions/*.py

# 2. Clean the database (drop existing tables and types)
# Connect to your database and run:
# DROP TABLE IF EXISTS users, api_keys, tenants, alembic_version CASCADE;
# DROP TYPE IF EXISTS userrole CASCADE;

# 3. Generate fresh migration from current models
uv run alembic revision --autogenerate -m "Fresh migration from models"

# 4. Apply the migration
uv run alembic upgrade head
```

### Option 2: Reset with Docker (If using Docker Compose)

If you're using the provided Docker setup for PostgreSQL:

```bash
# 1. Stop the database container
docker compose -f compose/postgres/docker-compose.yml down

# 2. Remove the database volume (WARNING: This deletes all data!)
docker volume rm nous_postgres-data

# 3. Remove migration files
rm -f migrations/versions/*.py

# 4. Restart the database
docker compose -f compose/postgres/docker-compose.yml up -d

# 5. Generate and apply fresh migrations
uv run alembic revision --autogenerate -m "Fresh migration from models"
uv run alembic upgrade head
```

### ⚠️ Important Notes

- **Data Loss**: Both options will permanently delete all data in your database
- **Review Generated Migrations**: Always inspect the generated migration files before applying them
- **Backup First**: If you have important data, back it up before resetting
- **Team Coordination**: If working in a team, coordinate resets to avoid conflicts
