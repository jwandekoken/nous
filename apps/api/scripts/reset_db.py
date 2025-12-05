import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add the parent directory to sys.path to allow importing app modules
# Assuming this script is run from the project root or apps/api/scripts
current_dir = Path(__file__).resolve().parent
api_root = current_dir.parent
sys.path.append(str(api_root))

from app.core.settings import get_settings


async def reset_database(delete_migrations: bool):
    """
    Reset the database by dropping and recreating the public schema,
    and dropping all tenant schemas (starting with nous_graph_).
    Optionally delete and regenerate migrations.
    """
    settings = get_settings()
    database_url = settings.database_url

    print(
        f"🔌 Connecting to database: {settings.postgres_db} on {settings.postgres_host}"
    )

    # Create async engine
    engine = create_async_engine(database_url, echo=False)

    try:
        async with engine.begin() as conn:
            # 0. Drop extensions (to clean up ag_catalog and others)
            print("🔌 Dropping extensions...")
            await conn.execute(text("DROP EXTENSION IF EXISTS age CASCADE;"))

            # 1. Drop all tenant schemas
            print("🔍 Finding tenant schemas...")
            result = await conn.execute(
                text(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'nous_graph_%';"
                )
            )
            tenant_schemas = result.scalars().all()

            if tenant_schemas:
                print(f"🗑️  Found {len(tenant_schemas)} tenant schemas. Dropping...")
                for schema in tenant_schemas:
                    print(f"   - Dropping schema: {schema}")
                    await conn.execute(
                        text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE;')
                    )
            else:
                print("ℹ️  No tenant schemas found.")

            # 2. Drop and recreate public schema
            print("🗑️  Dropping public schema...")
            await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))

            print("✨ Recreating public schema...")
            await conn.execute(text("CREATE SCHEMA public;"))

            # 3. Recreate extensions
            # AGE Extension is being created at the `apps/api/migrations/env.py` file, before applying the migrations

            print("✅ Database reset successfully.")

    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

    if delete_migrations:
        await manage_migrations(api_root)

    await apply_migrations(api_root)


async def manage_migrations(api_root: Path):
    """
    Delete existing migrations and generate a new initial migration.
    """
    migrations_dir = api_root / "migrations" / "versions"

    print("🗑️  Deleting existing migrations...")
    if migrations_dir.exists():
        for item in migrations_dir.iterdir():
            if item.is_file() and item.name != "__init__.py":
                item.unlink()

    print("📝 Generating new initial migration...")
    # Run alembic revision --autogenerate
    try:
        subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "initial_migration"],
            cwd=api_root,
            check=True,
        )
        print("✅ New migration generated.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating migration: {e}")
        sys.exit(1)


async def apply_migrations(api_root: Path):
    """
    Apply migrations to the database.
    """
    print("🚀 Applying migrations...")
    try:
        subprocess.run(["alembic", "upgrade", "head"], cwd=api_root, check=True)
        print("✅ Migrations applied successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error applying migrations: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Reset the database and optionally migrations."
    )
    parser.add_argument(
        "--delete-migrations",
        action="store_true",
        help="Delete existing migrations and regenerate from scratch.",
    )

    args = parser.parse_args()

    # Confirmation prompt
    print("⚠️  WARNING: This will DELETE ALL DATA in the database.")
    print("⚠️  This includes the 'public' schema and all 'nous_graph_*' schemas.")
    if args.delete_migrations:
        print("⚠️  WARNING: This will also DELETE ALL MIGRATION FILES.")

    confirm = input("Are you sure you want to continue? (y/N): ")
    if confirm.lower() != "y":
        print("Operation cancelled.")
        sys.exit(0)

    asyncio.run(reset_database(args.delete_migrations))


if __name__ == "__main__":
    main()
