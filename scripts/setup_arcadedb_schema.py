"""Script to set up the ArcadeDB schema.

This script connects to the ArcadeDB server and creates the necessary vertex types,
property types, and edge types as defined in the project's schema documentation.

To run this script, ensure that the ArcadeDB server is running and accessible,
and that the required environment variables for the database connection are set.

Usage:
    uv run python -m scripts.setup_arcadedb_schema
"""

import asyncio
import logging
import os
import sys

# Add project root to Python path to allow importing from 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.arcadedb.connection import (
    close_graph_db,
    get_database_name,
    get_graph_db,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# ArcadeDB Schema Definition - Clean DDL statements in correct order
SCHEMA_STATEMENTS = [
    # First create vertex types
    "CREATE VERTEX TYPE Entity IF NOT EXISTS",
    "CREATE VERTEX TYPE Identifier IF NOT EXISTS",
    "CREATE VERTEX TYPE Fact IF NOT EXISTS",
    "CREATE VERTEX TYPE Source IF NOT EXISTS",
    # Then create edge types
    "CREATE EDGE TYPE HAS_IDENTIFIER IF NOT EXISTS",
    "CREATE EDGE TYPE HAS_FACT IF NOT EXISTS",
    "CREATE EDGE TYPE DERIVED_FROM IF NOT EXISTS",
    # Then create properties for Entity
    "CREATE PROPERTY Entity.id IF NOT EXISTS STRING (mandatory true)",
    "CREATE PROPERTY Entity.created_at IF NOT EXISTS DATETIME (mandatory true, default sysdate('YYYY-MM-DD HH:MM:SS'))",
    "CREATE PROPERTY Entity.metadata IF NOT EXISTS MAP",
    # Properties for Identifier
    "CREATE PROPERTY Identifier.value IF NOT EXISTS STRING (mandatory true)",
    "CREATE PROPERTY Identifier.type IF NOT EXISTS STRING",
    # Properties for Fact
    "CREATE PROPERTY Fact.fact_id IF NOT EXISTS STRING (mandatory true)",
    "CREATE PROPERTY Fact.name IF NOT EXISTS STRING",
    "CREATE PROPERTY Fact.type IF NOT EXISTS STRING",
    # Properties for Source
    "CREATE PROPERTY Source.id IF NOT EXISTS STRING (mandatory true)",
    "CREATE PROPERTY Source.content IF NOT EXISTS STRING",
    "CREATE PROPERTY Source.timestamp IF NOT EXISTS DATETIME",
    # Properties for edges
    "CREATE PROPERTY HAS_IDENTIFIER.is_primary IF NOT EXISTS BOOLEAN",
    "CREATE PROPERTY HAS_IDENTIFIER.created_at IF NOT EXISTS DATETIME (default sysdate('YYYY-MM-DD HH:MM:SS'))",
    "CREATE PROPERTY HAS_FACT.verb IF NOT EXISTS STRING",
    "CREATE PROPERTY HAS_FACT.confidence_score IF NOT EXISTS DOUBLE",
    "CREATE PROPERTY HAS_FACT.created_at IF NOT EXISTS DATETIME (default sysdate('YYYY-MM-DD HH:MM:SS'))",
    # Finally create indexes
    "CREATE INDEX IF NOT EXISTS ON Entity (id) UNIQUE",
    "CREATE INDEX IF NOT EXISTS ON Identifier (value) UNIQUE",
    "CREATE INDEX IF NOT EXISTS ON Fact (fact_id) UNIQUE",
    "CREATE INDEX IF NOT EXISTS ON Source (id) UNIQUE",
]


async def setup_schema():
    """Sets up the ArcadeDB schema by executing the DDL commands."""
    db_client = None
    try:
        logging.info("Connecting to ArcadeDB...")
        db_client = await get_graph_db()
        database_name = get_database_name()
        logging.info(f"Connected to database: {database_name}")

        logging.info(f"Executing {len(SCHEMA_STATEMENTS)} schema setup commands...")

        successful_commands = 0
        failed_commands = 0

        for i, statement in enumerate(SCHEMA_STATEMENTS, 1):
            try:
                logging.info(
                    f"Executing statement {i}/{len(SCHEMA_STATEMENTS)}: {statement[:50]}..."
                )

                # Execute DDL statement
                result = await db_client.execute_command(
                    command=statement,
                    database=database_name,
                    language="sql",
                )

                logging.info(f"Statement {i} result: {result}")
                successful_commands += 1

            except Exception as e:
                logging.error(f"Statement {i} failed: {e}")
                failed_commands += 1

        logging.info(
            f"Schema setup completed. Successful: {successful_commands}, Failed: {failed_commands}"
        )

        if failed_commands > 0:
            logging.warning(
                f"{failed_commands} statements failed. This may be expected if the schema already exists."
            )

    except Exception as e:
        logging.error(f"An error occurred during schema setup: {e}", exc_info=True)
    finally:
        if db_client:
            logging.info("Closing ArcadeDB connection.")
            await close_graph_db()


if __name__ == "__main__":
    asyncio.run(setup_schema())
