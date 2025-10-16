"""PostgreSQL AGE implementation of the graph repository protocol."""

import json
from datetime import datetime
from typing import Any, cast, override
from uuid import UUID

import asyncpg

from app.core.settings import get_settings
from app.features.graph.models import (
    DerivedFrom,
    Entity,
    Fact,
    HasFact,
    HasIdentifier,
    Identifier,
    Source,
)
from app.features.graph.repositories.base import GraphRepository
from app.features.graph.repositories.types import (
    AddFactToEntityResult,
    CreateEntityResult,
    FactWithOptionalSource,
    FactWithSource,
    FindEntityByIdResult,
    FindEntityResult,
    IdentifierWithRelationship,
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
        Creates a new entity with an identifier using an idempotent approach.

        This method first checks if an entity already exists for the given identifier.
        If it exists, returns the existing entity. If not, creates a new one.
        """

        # Check if entity already exists for this identifier
        existing_entity = await self.find_entity_by_identifier(
            identifier.value, identifier.type
        )

        if existing_entity is not None:
            # Return existing entity with its identifier and relationship
            return {
                "entity": existing_entity["entity"],
                "identifier": existing_entity["identifier"]["identifier"],
                "relationship": existing_entity["identifier"]["relationship"],
            }

        # Entity doesn't exist, create it
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

        if not record:
            raise RuntimeError(
                "Failed to create entity, the query returned no results."
            )

        # Extract the result string from the agtype, clean it, and parse it as JSON
        record = cast(asyncpg.Record, record)
        result_str = cast(str, record["result"])

        cleaned_result_str = self._clean_agtype_string(result_str)
        result_map = cast(dict[str, Any], json.loads(cleaned_result_str))

        # Extract properties from the agtype objects
        entity_props = cast(dict[str, Any], result_map["entity"]["properties"])
        identifier_props = cast(dict[str, Any], result_map["identifier"]["properties"])
        relationship_props = cast(
            dict[str, Any], result_map["relationship"]["properties"]
        )

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
        cypher_query = f"""
        MATCH (e:Entity)-[r:HAS_IDENTIFIER]->(i:Identifier {{
            value: '{self._escape_cypher_string(identifier_value)}',
            type: '{self._escape_cypher_string(identifier_type)}'
        }})
        OPTIONAL MATCH (e)-[hf:HAS_FACT]->(f:Fact)
        OPTIONAL MATCH (f)-[df:DERIVED_FROM]->(s:Source)
        RETURN collect(DISTINCT {{
            entity: e,
            identifier: i,
            relationship: r,
            fact: f,
            source: s,
            fact_relationship: hf
        }}) AS result
        """

        record = await self._execute_cypher(
            cypher_query=cypher_query,
            as_clause="as (result agtype)",
            fetch_mode="row",
        )
        print(f"----------> Record: {record}")

        if not record:
            return None

        record = cast(asyncpg.Record, record)
        result_str = cast(str, record["result"])
        cleaned_result_str = self._clean_agtype_string(result_str)
        results_list = cast(list[dict[str, Any]], json.loads(cleaned_result_str))
        print(f"----------> Results list: {results_list}")
        if not results_list:
            return None

        # The first result contains the entity and identifier info
        first_result = results_list[0]

        # Extract entity
        entity_props = cast(dict[str, Any], first_result["entity"]["properties"])
        entity = Entity(
            id=UUID(entity_props["id"]),
            created_at=datetime.fromisoformat(entity_props["created_at"]),
            metadata=json.loads(entity_props["metadata"])
            if entity_props["metadata"]
            else {},
        )

        # Extract identifier and relationship
        identifier_props = cast(
            dict[str, Any], first_result["identifier"]["properties"]
        )
        relationship_props = cast(
            dict[str, Any], first_result["relationship"]["properties"]
        )

        identifier = Identifier(
            value=identifier_props["value"],
            type=identifier_props["type"],
        )

        has_identifier_rel = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=identifier.value,
            is_primary=relationship_props["is_primary"],
            created_at=datetime.fromisoformat(relationship_props["created_at"]),
        )

        identifier_with_rel: IdentifierWithRelationship = {
            "identifier": identifier,
            "relationship": has_identifier_rel,
        }

        # Build facts with sources from all results
        facts_with_sources: list[FactWithSource] = []

        for result_item in results_list:
            fact_data = result_item.get("fact")
            if not fact_data:  # Skip if no fact
                continue

            fact_props = cast(dict[str, Any], fact_data["properties"])
            fact = Fact(
                name=fact_props["name"],
                type=fact_props["type"],
            )

            # Verify fact_id matches (should be computed by model validator)
            if fact.fact_id != fact_props["fact_id"]:
                continue

            # At this point we know fact.fact_id is not None
            assert fact.fact_id is not None

            source = None
            source_data = result_item.get("source")
            if source_data:
                source_props = cast(dict[str, Any], source_data["properties"])
                source = Source(
                    id=UUID(source_props["id"]),
                    content=source_props["content"],
                    timestamp=datetime.fromisoformat(source_props["timestamp"]),
                )

            fact_rel_props = cast(
                dict[str, Any], result_item["fact_relationship"]["properties"]
            )
            has_fact_rel = HasFact(
                from_entity_id=entity.id,
                to_fact_id=fact.fact_id,
                verb=fact_rel_props["verb"],
                confidence_score=fact_rel_props["confidence_score"],
                created_at=datetime.fromisoformat(fact_rel_props["created_at"]),
            )

            fact_with_source: FactWithSource = {
                "fact": fact,
                "source": source,
                "relationship": has_fact_rel,
            }
            facts_with_sources.append(fact_with_source)

        return {
            "entity": entity,
            "identifier": identifier_with_rel,
            "facts_with_sources": facts_with_sources,
        }

    @override
    async def find_entity_by_id(self, entity_id: str) -> FindEntityByIdResult | None:
        """Find an entity by its ID."""
        cypher_query = f"""
        MATCH (e:Entity {{id: '{entity_id}'}})
        OPTIONAL MATCH (e)-[r:HAS_IDENTIFIER]->(i:Identifier)
        OPTIONAL MATCH (e)-[hf:HAS_FACT]->(f:Fact)
        OPTIONAL MATCH (f)-[df:DERIVED_FROM]->(s:Source)
        RETURN collect(DISTINCT {{
            entity: e,
            identifier: i,
            relationship: r,
            fact: f,
            source: s,
            fact_relationship: hf
        }}) AS result
        """

        record = await self._execute_cypher(
            cypher_query=cypher_query,
            as_clause="as (result agtype)",
            fetch_mode="row",
        )

        if not record:
            return None

        record = cast(asyncpg.Record, record)
        result_str = cast(str, record["result"])
        cleaned_result_str = self._clean_agtype_string(result_str)
        results_list = cast(list[dict[str, Any]], json.loads(cleaned_result_str))

        if not results_list:
            return None

        # The first result contains the entity info
        first_result = results_list[0]

        # Extract entity
        entity_props = cast(dict[str, Any], first_result["entity"]["properties"])
        entity = Entity(
            id=UUID(entity_props["id"]),
            created_at=datetime.fromisoformat(entity_props["created_at"]),
            metadata=json.loads(entity_props["metadata"])
            if entity_props["metadata"]
            else {},
        )

        # Find the primary identifier (or first one if no primary exists)
        identifier_with_rel: IdentifierWithRelationship | None = None

        for result_item in results_list:
            identifier_data = result_item.get("identifier")
            relationship_data = result_item.get("relationship")

            if identifier_data and relationship_data:
                identifier_props = cast(dict[str, Any], identifier_data["properties"])
                relationship_props = cast(
                    dict[str, Any], relationship_data["properties"]
                )

                identifier = Identifier(
                    value=identifier_props["value"],
                    type=identifier_props["type"],
                )

                has_identifier_rel = HasIdentifier(
                    from_entity_id=entity.id,
                    to_identifier_value=identifier.value,
                    is_primary=relationship_props["is_primary"],
                    created_at=datetime.fromisoformat(relationship_props["created_at"]),
                )

                # Prefer primary identifier, but take the first one if none is primary
                if identifier_with_rel is None or relationship_props["is_primary"]:
                    identifier_with_rel = {
                        "identifier": identifier,
                        "relationship": has_identifier_rel,
                    }

                    # If this is primary, we can stop looking
                    if relationship_props["is_primary"]:
                        break

        # Build facts with sources from all results
        facts_with_sources: list[FactWithSource] = []

        for result_item in results_list:
            fact_data = result_item.get("fact")
            if not fact_data:  # Skip if no fact
                continue

            fact_props = cast(dict[str, Any], fact_data["properties"])
            fact = Fact(
                name=fact_props["name"],
                type=fact_props["type"],
            )

            # Verify fact_id matches (should be computed by model validator)
            if fact.fact_id != fact_props["fact_id"]:
                continue

            # At this point we know fact.fact_id is not None
            assert fact.fact_id is not None

            source = None
            source_data = result_item.get("source")
            if source_data:
                source_props = cast(dict[str, Any], source_data["properties"])
                source = Source(
                    id=UUID(source_props["id"]),
                    content=source_props["content"],
                    timestamp=datetime.fromisoformat(source_props["timestamp"]),
                )

            fact_rel_props = cast(
                dict[str, Any], result_item["fact_relationship"]["properties"]
            )
            has_fact_rel = HasFact(
                from_entity_id=entity.id,
                to_fact_id=fact.fact_id,
                verb=fact_rel_props["verb"],
                confidence_score=fact_rel_props["confidence_score"],
                created_at=datetime.fromisoformat(fact_rel_props["created_at"]),
            )

            fact_with_source: FactWithSource = {
                "fact": fact,
                "source": source,
                "relationship": has_fact_rel,
            }
            facts_with_sources.append(fact_with_source)

        return {
            "entity": entity,
            "identifier": identifier_with_rel,
            "facts_with_sources": facts_with_sources,
        }

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
        """
        Add a fact to an entity with its source using an idempotent approach.

        This method creates or updates the fact, source, and relationships in the graph.
        If create_source is False, it will only create the relationship to an existing source.
        """
        # Ensure fact_id is set
        if fact.fact_id is None:
            raise ValueError("Fact must have a fact_id set")

        # First check if the entity exists
        entity_check = await self.find_entity_by_id(entity_id)
        if entity_check is None:
            raise ValueError(f"Entity with ID '{entity_id}' does not exist")

        # Check if the HAS_FACT relationship already exists
        check_query = f"""
        MATCH (e:Entity {{id: '{entity_id}'}})-[hf:HAS_FACT {{
            verb: '{self._escape_cypher_string(verb)}'
        }}]->(f:Fact {{fact_id: '{fact.fact_id}'}})
        RETURN hf AS relationship
        """

        existing_rel = await self._execute_cypher(
            cypher_query=check_query,
            as_clause="as (relationship agtype)",
            fetch_mode="row",
        )

        if existing_rel:
            # Relationship already exists, return the existing data
            # Get the full data by finding the entity
            found = await self.find_entity_by_id(entity_id)
            if found and found["facts_with_sources"]:
                # Find the matching fact
                for fact_with_source in found["facts_with_sources"]:
                    if (
                        fact_with_source["fact"].fact_id == fact.fact_id
                        and fact_with_source["relationship"].verb == verb
                    ):
                        if fact_with_source["source"] is None:
                            raise RuntimeError(
                                "Existing fact relationship found but source is missing"
                            )
                        derived_from_rel = DerivedFrom(
                            from_fact_id=fact.fact_id,
                            to_source_id=fact_with_source["source"].id,
                        )
                        return {
                            "fact": fact_with_source["fact"],
                            "source": fact_with_source["source"],
                            "has_fact_relationship": fact_with_source["relationship"],
                            "derived_from_relationship": derived_from_rel,
                        }
            raise RuntimeError("Relationship exists but could not retrieve data")

        # Relationship doesn't exist, create it
        cypher_query = f"""
        MATCH (e:Entity {{id: '{entity_id}'}})
        MERGE (f:Fact {{
            fact_id: '{fact.fact_id}',
            name: '{self._escape_cypher_string(fact.name)}',
            type: '{self._escape_cypher_string(fact.type)}'
        }})
        MERGE (s:Source {{
            id: '{source.id}',
            content: '{self._escape_cypher_string(source.content)}',
            timestamp: '{source.timestamp.isoformat()}'
        }})
        CREATE (e)-[hf:HAS_FACT {{
            verb: '{self._escape_cypher_string(verb)}',
            confidence_score: {confidence_score},
            created_at: '{datetime.now().isoformat()}'
        }}]->(f)
        MERGE (f)-[df:DERIVED_FROM]->(s)
        RETURN {{
            fact: f,
            source: s,
            has_fact_relationship: hf,
            derived_from_relationship: df
        }} AS result
        """

        # Execute the query using the helper method
        record = await self._execute_cypher(
            cypher_query=cypher_query,
            as_clause="as (result agtype)",
            fetch_mode="row",
        )

        if not record:
            raise RuntimeError(
                f"Failed to add fact '{fact.fact_id}' to entity '{entity_id}', the query returned no results."
            )

        # Extract the result string from the agtype, clean it, and parse it as JSON
        record = cast(asyncpg.Record, record)
        result_str = cast(str, record["result"])

        cleaned_result_str = self._clean_agtype_string(result_str)
        result_map = cast(dict[str, Any], json.loads(cleaned_result_str))

        # Extract properties from the agtype objects
        fact_props = cast(dict[str, Any], result_map["fact"]["properties"])
        source_props = cast(dict[str, Any], result_map["source"]["properties"])
        has_fact_props = cast(
            dict[str, Any], result_map["has_fact_relationship"]["properties"]
        )

        # Reconstruct the objects
        # Note: fact_id is automatically computed by the model validator from name and type
        created_fact = Fact(
            name=fact_props["name"],
            type=fact_props["type"],
        )
        # Verify the fact_id matches what we expect
        if created_fact.fact_id != fact_props["fact_id"]:
            raise RuntimeError(
                f"Fact ID mismatch: expected '{fact_props['fact_id']}', got '{created_fact.fact_id}'"
            )

        created_source = Source(
            id=UUID(source_props["id"]),
            content=source_props["content"],
            timestamp=datetime.fromisoformat(source_props["timestamp"]),
        )

        created_has_fact = HasFact(
            from_entity_id=UUID(entity_id),
            to_fact_id=created_fact.fact_id,
            verb=has_fact_props["verb"],
            confidence_score=has_fact_props["confidence_score"],
            created_at=datetime.fromisoformat(has_fact_props["created_at"]),
        )

        # Note: DerivedFrom relationship doesn't have additional properties beyond the connection
        derived_from_rel = DerivedFrom(
            from_fact_id=created_fact.fact_id,
            to_source_id=created_source.id,
        )

        return {
            "fact": created_fact,
            "source": created_source,
            "has_fact_relationship": created_has_fact,
            "derived_from_relationship": derived_from_rel,
        }

    @override
    async def find_fact_by_id(self, fact_id: str) -> FactWithOptionalSource | None:
        """Find a fact by its ID."""
        raise NotImplementedError()
