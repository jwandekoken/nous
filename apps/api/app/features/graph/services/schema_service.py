"""Service for managing graph schema."""

import asyncpg


class GraphSchemaService:
    """Service to manage the schema of AGE graphs."""

    @staticmethod
    async def setup_graph_schema(conn: asyncpg.Connection, graph_name: str) -> None:
        """Create the necessary labels and schema for a graph.

        Args:
            conn: Database connection
            graph_name: Name of the AGE graph
        """
        # Create vertex labels
        await conn.execute(f"SELECT create_vlabel('{graph_name}', 'Entity');")
        await conn.execute(f"SELECT create_vlabel('{graph_name}', 'Identifier');")
        await conn.execute(f"SELECT create_vlabel('{graph_name}', 'Fact');")
        await conn.execute(f"SELECT create_vlabel('{graph_name}', 'Source');")

        # Create edge labels
        await conn.execute(f"SELECT create_elabel('{graph_name}', 'HAS_IDENTIFIER');")
        await conn.execute(f"SELECT create_elabel('{graph_name}', 'HAS_FACT');")
        await conn.execute(f"SELECT create_elabel('{graph_name}', 'DERIVED_FROM');")

    @staticmethod
    async def create_graph_and_schema(
        conn: asyncpg.Connection, graph_name: str
    ) -> None:
        """Create a new graph and set up its schema.

        Args:
            conn: Database connection
            graph_name: Name of the AGE graph
        """
        # Load AGE extension for this session
        await conn.execute("LOAD 'age';")
        await conn.execute("SET search_path = ag_catalog, '$user', public;")

        # Create graph
        await conn.execute("SELECT create_graph($1)", graph_name)

        # Setup schema
        await GraphSchemaService.setup_graph_schema(conn, graph_name)
