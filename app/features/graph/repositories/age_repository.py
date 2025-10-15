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

    async def _setup_age_connection(self, conn: asyncpg.Connection) -> None:
        """Setup AGE extension and search path for a connection."""
        _ = await conn.execute("LOAD 'age';")
        _ = await conn.execute("SET search_path = ag_catalog, '$user', public;")

    async def _execute_cypher(
        self,
        query: str,
        fetch_mode: str = "row",
    ) -> asyncpg.Record | list[asyncpg.Record] | str | None:
        """
        Execute a Cypher query through AGE with proper connection setup.

        Args:
            query: The complete SQL query to execute (already formatted for AGE)
            fetch_mode: "row" for fetchrow, "all" for fetch, "none" for execute

        Returns:
            Query result based on fetch_mode:
            - "row": Single record or None
            - "all": List of records
            - "none": Execution status string
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
        RETURN
            e.id AS entity_id,
            e.created_at AS entity_created_at,
            e.metadata AS entity_metadata,
            i.value AS identifier_value,
            i.type AS identifier_type,
            r.is_primary AS is_primary,
            r.created_at AS rel_created_at
        """

        # Build the complete AGE SQL query
        query = f"""
        SELECT * FROM cypher('{self.graph_name}', $${cypher_query}$$)
        as (entity_id agtype, entity_created_at agtype, entity_metadata agtype, identifier_value agtype, identifier_type agtype, is_primary agtype, rel_created_at agtype);
        """

        # Execute the query using our helper method
        record = await self._execute_cypher(query)

        print(f"----------> Record: {record}")

        if not record:
            raise RuntimeError(
                "Failed to create or find entity, the query returned no results."
            )

        # Map the record back to your Pydantic models
        # agtype returns values as strings with quotes, so we need to strip and parse them
        # AGE escapes the JSON when storing, so we need to decode the escape sequences
        metadata_str = record["entity_metadata"].strip('"')
        # Replace escaped quotes with regular quotes
        metadata_str = metadata_str.replace('\\"', '"')

        created_entity = Entity(
            id=UUID(record["entity_id"].strip('"')),
            created_at=datetime.fromisoformat(record["entity_created_at"].strip('"')),
            # Parse the unescaped JSON
            metadata=json.loads(metadata_str) if metadata_str else {},
        )

        created_identifier = Identifier(
            value=record["identifier_value"].strip('"'),
            type=record["identifier_type"].strip('"'),
        )

        created_relationship = HasIdentifier(
            from_entity_id=created_entity.id,
            to_identifier_value=created_identifier.value,
            is_primary=record["is_primary"],
            created_at=datetime.fromisoformat(record["rel_created_at"].strip('"')),
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
