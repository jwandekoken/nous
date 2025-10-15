"""PostgreSQL AGE implementation of the graph repository protocol."""

import json
from datetime import datetime
from typing import cast, override
from uuid import UUID

import asyncpg

from app.core.settings import get_settings
from app.features.graph.models import Entity, Fact, HasIdentifier, Identifier, Source
from app.features.graph.repositories.base import GraphRepository
from app.features.graph.repositories.types import (
    AddFactToEntityResult,
    CreateEntityResult,
    FactWithOptionalSource,
    FindEntityByIdResult,
    FindEntityResult,
)


class AgeRepository(GraphRepository):
    """PostgreSQL AGE implementation of the graph repository."""

    pool: asyncpg.Pool
    graph_name: str

    def __init__(self, pool: asyncpg.Pool):
        """Initialize the repository with a database connection pool."""
        self.pool = pool
        self.graph_name = get_settings().age_graph_name

    @staticmethod
    def _escape_cypher_string(value: str) -> str:
        """Escape single quotes for use in Cypher string literals."""
        return value.replace("'", "\\'")

    @staticmethod
    def _clean_agtype_string(agtype_str: str) -> str:
        """Clean AGE agtype string by removing type annotations like ::vertex and ::edge."""
        import re

        # Remove ::vertex and ::edge annotations
        return re.sub(r"::(vertex|edge)", "", agtype_str)

    async def _setup_age_connection(self, conn: asyncpg.Connection) -> None:
        """Setup AGE extension and search path for a connection."""
        _ = await conn.execute("LOAD 'age';")
        _ = await conn.execute("SET search_path = ag_catalog, '$user', public;")

    async def _execute_cypher(
        self,
        cypher_query: str,
        as_clause: str,
        fetch_mode: str = "row",
    ) -> asyncpg.Record | list[asyncpg.Record] | str | None:
        """
        Execute a Cypher query by wrapping it in the necessary SQL.

        Args:
            cypher_query: The raw Cypher query string.
            as_clause: The complete AS clause string, e.g., "as (result agtype)".
            fetch_mode: "row" for fetchrow, "all" for fetch, "none" for execute.

        Returns:
            Query result based on fetch_mode.
        """
        if not as_clause.strip().lower().startswith("as"):
            raise ValueError("The 'as_clause' must start with 'AS'.")

        # Build the complete AGE SQL query using the provided as_clause
        query = f"""
            SELECT * FROM cypher('{self.graph_name}', $${cypher_query}$$)
            {as_clause};
        """

        async with self.pool.acquire() as conn:
            conn = cast(asyncpg.Connection, conn)

            async with conn.transaction():
                await self._setup_age_connection(conn)

                if fetch_mode == "row":
                    return await conn.fetchrow(query)
                elif fetch_mode == "all":
                    return await conn.fetch(query)
                else:  # "none"
                    return await conn.execute(query)

    @override
    async def create_entity(
        self, entity: Entity, identifier: Identifier, relationship: HasIdentifier
    ) -> CreateEntityResult:
        """
        Creates a new entity with an identifier using an idempotent Cypher query.

        This method uses MERGE to find or create an Identifier node and then
        finds or creates the associated Entity and the HAS_IDENTIFIER relationship.
        Since AGE doesn't support ON CREATE SET, the MERGE includes all properties.
        """

        # Convert Python boolean to Cypher boolean (lowercase)
        is_primary_str = str(relationship.is_primary).lower()

        # Prepare metadata JSON - use it directly as agtype without extra escaping
        metadata_json = json.dumps(entity.metadata or {}).replace(
            "'", "''"
        )  # Double single quotes for SQL

        # Build the Cypher query with embedded parameters
        # AGE cypher function expects the query as a dollar-quoted string
        # We use MERGE for idempotency - it will find or create
        # Note: AGE doesn't support ON CREATE SET, so we include all properties in MERGE
        cypher_query = f"""
        MERGE (i:Identifier {{value: '{self._escape_cypher_string(identifier.value)}', type: '{self._escape_cypher_string(identifier.type)}'}})
        MERGE (e:Entity {{id: '{entity.id}', created_at: '{entity.created_at.isoformat()}', metadata: '{metadata_json}'::agtype}})
        MERGE (e)-[r:HAS_IDENTIFIER {{is_primary: {is_primary_str}, created_at: '{relationship.created_at.isoformat()}'}}]->(i)
        RETURN {{
            entity: e,
            identifier: i,
            relationship: r
        }} AS result
        """

        # Execute the query using the new helper method
        record = await self._execute_cypher(
            cypher_query=cypher_query,
            as_clause="as (result agtype)",
            fetch_mode="row",
        )

        print(f"----------> Record: {record}")

        if not record:
            raise RuntimeError(
                "Failed to create or find entity, the query returned no results."
            )

        # Extract the result string from the agtype, clean it, and parse it as JSON
        result_str = record["result"]
        print(f"----------> Result string: {result_str}")

        cleaned_result_str = self._clean_agtype_string(result_str)
        result_map = json.loads(cleaned_result_str)

        # Extract properties from the agtype objects
        entity_props = result_map["entity"]["properties"]
        identifier_props = result_map["identifier"]["properties"]
        relationship_props = result_map["relationship"]["properties"]

        created_entity = Entity(
            id=UUID(entity_props["id"]),
            created_at=datetime.fromisoformat(entity_props["created_at"]),
            metadata=json.loads(entity_props["metadata"])
            if entity_props["metadata"]
            else {},
        )

        created_identifier = Identifier(
            value=identifier_props["value"],
            type=identifier_props["type"],
        )

        created_relationship = HasIdentifier(
            from_entity_id=created_entity.id,
            to_identifier_value=created_identifier.value,
            is_primary=relationship_props["is_primary"],
            created_at=datetime.fromisoformat(relationship_props["created_at"]),
        )

        return {
            "entity": created_entity,
            "identifier": created_identifier,
            "relationship": created_relationship,
        }

    @override
    async def find_entity_by_identifier(
        self, identifier_value: str, identifier_type: str
    ) -> FindEntityResult | None:
        """Find an entity by its identifier."""
        raise NotImplementedError()

    @override
    async def find_entity_by_id(self, entity_id: str) -> FindEntityByIdResult | None:
        """Find an entity by its ID."""
        raise NotImplementedError()

    @override
    async def delete_entity_by_id(self, entity_id: str) -> bool:
        """Delete an entity by its ID."""
        raise NotImplementedError()

    @override
    async def add_fact_to_entity(
        self,
        entity_id: str,
        fact: Fact,
        source: Source,
        verb: str,
        confidence_score: float = 1.0,
        create_source: bool = True,
    ) -> AddFactToEntityResult:
        """Add a fact to an entity."""
        raise NotImplementedError()

    @override
    async def find_fact_by_id(self, fact_id: str) -> FactWithOptionalSource | None:
        """Find a fact by its ID."""
        raise NotImplementedError()
