"""Script to set up the PostgreSQL database schema for the graph."""

import asyncio

from app.core.settings import get_settings
from app.db.postgres.connection import close_db_pool, get_db_pool


async def setup_schema() -> None:
    """Create the graph and set up the schema."""
    settings = get_settings()
    pool = await get_db_pool()
    async with pool.acquire() as connection:
        print("Creating AGE extension...")
        await connection.execute("CREATE EXTENSION IF NOT EXISTS age;")

        print("Loading AGE extension...")
        await connection.execute("LOAD 'age';")

        print("Setting search path...")
        await connection.execute("SET search_path = ag_catalog, '$user', public;")

        graph_name = settings.age_graph_name

        # Delete the old knowledge_graph if it exists
        old_graph_exists = await connection.fetchval(
            "SELECT 1 FROM ag_graph WHERE name = $1;", "knowledge_graph"
        )
        if old_graph_exists:
            print("Deleting old 'knowledge_graph'...")
            await connection.execute("SELECT drop_graph('knowledge_graph', true);")
            print("Old graph deleted.")

        print(f"Creating graph '{graph_name}'...")

        # Check if graph exists
        graph_exists = await connection.fetchval(
            "SELECT 1 FROM ag_graph WHERE name = $1;", graph_name
        )
        if not graph_exists:
            await connection.execute(f"SELECT create_graph('{graph_name}');")
            print(f"Graph '{graph_name}' created.")
        else:
            print(f"Graph '{graph_name}' already exists.")

        print("Creating vertex labels...")
        # Create vertex labels if they don't exist
        await connection.execute(f"SELECT create_vlabel('{graph_name}', 'Entity');")
        await connection.execute(f"SELECT create_vlabel('{graph_name}', 'Identifier');")
        await connection.execute(f"SELECT create_vlabel('{graph_name}', 'Fact');")
        await connection.execute(f"SELECT create_vlabel('{graph_name}', 'Source');")

        print("Creating edge labels...")
        # Create edge labels if they don't exist
        await connection.execute(
            f"SELECT create_elabel('{graph_name}', 'HAS_IDENTIFIER');"
        )
        await connection.execute(f"SELECT create_elabel('{graph_name}', 'HAS_FACT');")
        await connection.execute(f"SELECT create_elabel('{graph_name}', 'HAS_SOURCE');")

        print("Schema setup complete.")


async def main() -> None:
    """Main function to run the schema setup."""
    try:
        await setup_schema()
    finally:
        await close_db_pool()


if __name__ == "__main__":
    print("Starting database schema setup...")
    asyncio.run(main())
