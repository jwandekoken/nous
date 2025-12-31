"""PostgreSQL AGE implementation of the graph repository protocol."""

import json
from datetime import datetime
from typing import Any, cast, override
from uuid import UUID

import asyncpg

from app.features.graph.models import (
    DerivedFrom,
    Entity,
    Fact,
    HasFact,
    HasIdentifier,
    Identifier,
    Source,
)
from app.features.graph.repositories.protocols import (
    AddFactToEntityResult,
    CreateEntityResult,
    FactWithOptionalSource,
    FactWithSource,
    FindEntityByIdResult,
    FindEntityResult,
    GraphRepository,
    IdentifierWithRelationship,
)


class AgeRepository(GraphRepository):
    """PostgreSQL AGE implementation of the graph repository."""

    pool: asyncpg.Pool
    graph_name: str

    def __init__(self, pool: asyncpg.Pool, graph_name: str):
        """Initialize the repository with a database connection pool and graph name."""
        self.pool = pool
        self.graph_name = graph_name
        if not graph_name:
            raise ValueError("graph_name must be provided")

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

        if not record:
            return None

        record = cast(asyncpg.Record, record)
        result_str = cast(str, record["result"])
        cleaned_result_str = self._clean_agtype_string(result_str)
        results_list = cast(list[dict[str, Any]], json.loads(cleaned_result_str))
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
        # First check if entity exists
        entity_check = await self.find_entity_by_id(entity_id)
        if entity_check is None:
            return False

        # Get facts connected to this entity before deletion
        entity_data = entity_check

        # For each fact connected to this entity, check if it's used by other entities
        facts_to_delete = []
        for fact_data in entity_data["facts_with_sources"]:
            fact_id = fact_data["fact"].fact_id
            assert fact_id is not None

            # Check if this fact is used by other entities
            check_query = f"""
            MATCH (f:Fact {{fact_id: '{fact_id}'}})
            MATCH (e:Entity)-[:HAS_FACT]->(f)
            RETURN count(e) AS usage_count
            """

            record = await self._execute_cypher(
                cypher_query=check_query,
                as_clause="as (usage_count agtype)",
                fetch_mode="row",
            )

            if record:
                record = cast(asyncpg.Record, record)
                usage_count_str = cast(str, record["usage_count"])
                usage_count = int(usage_count_str)

                # If only used by this entity (usage_count == 1), mark for deletion
                if usage_count == 1:
                    facts_to_delete.append(fact_id)

        # Now perform the cascading delete
        # 1. Delete HAS_FACT relationships for this entity
        # 2. Delete HAS_IDENTIFIER relationships for this entity
        # 3. Delete facts that are only used by this entity
        # 4. Delete sources that are no longer referenced
        # 5. Delete identifiers that are no longer referenced
        # 6. Delete the entity itself

        # Delete HAS_FACT relationships for this entity
        delete_has_fact_query = f"""
        MATCH (e:Entity {{id: '{entity_id}'}})-[hf:HAS_FACT]->(f:Fact)
        DETACH DELETE hf
        RETURN count(hf) AS deleted_count
        """

        await self._execute_cypher(
            cypher_query=delete_has_fact_query,
            as_clause="as (deleted_count agtype)",
            fetch_mode="row",
        )

        # Delete HAS_IDENTIFIER relationships for this entity
        delete_has_identifier_query = f"""
        MATCH (e:Entity {{id: '{entity_id}'}})-[hi:HAS_IDENTIFIER]->(i:Identifier)
        DETACH DELETE hi
        RETURN count(hi) AS deleted_count
        """

        await self._execute_cypher(
            cypher_query=delete_has_identifier_query,
            as_clause="as (deleted_count agtype)",
            fetch_mode="row",
        )

        # Delete the entity itself
        delete_entity_query = f"""
        MATCH (e:Entity {{id: '{entity_id}'}})
        DETACH DELETE e
        RETURN true AS entity_deleted
        """

        record = await self._execute_cypher(
            cypher_query=delete_entity_query,
            as_clause="as (entity_deleted agtype)",
            fetch_mode="row",
        )

        if not record:
            raise RuntimeError(f"Failed to delete entity '{entity_id}'")

        # Now delete facts that were only used by this entity
        for fact_id in facts_to_delete:
            # Get the source ID before deleting the fact
            source_query = f"""
            MATCH (f:Fact {{fact_id: '{fact_id}'}})
            OPTIONAL MATCH (f)-[:DERIVED_FROM]->(s:Source)
            RETURN s.id AS source_id
            """

            source_record = await self._execute_cypher(
                cypher_query=source_query,
                as_clause="as (source_id agtype)",
                fetch_mode="row",
            )

            # Delete the fact
            delete_fact_query = f"""
            MATCH (f:Fact {{fact_id: '{fact_id}'}})
            DETACH DELETE f
            RETURN true AS fact_deleted
            """

            await self._execute_cypher(
                cypher_query=delete_fact_query,
                as_clause="as (fact_deleted agtype)",
                fetch_mode="row",
            )

            # Check if source should be deleted (no longer referenced by any facts)
            if source_record:
                source_record = cast(asyncpg.Record, source_record)
                source_id_str = cast(str, source_record["source_id"])

                if source_id_str != "null":
                    # Check if source is still used by other facts
                    check_source_usage = f"""
                    MATCH (s:Source {{id: '{source_id_str}'}})
                    OPTIONAL MATCH (f:Fact)-[:DERIVED_FROM]->(s)
                    RETURN count(f) AS usage_count
                    """

                    usage_record = await self._execute_cypher(
                        cypher_query=check_source_usage,
                        as_clause="as (usage_count agtype)",
                        fetch_mode="row",
                    )

                    if usage_record:
                        usage_record = cast(asyncpg.Record, usage_record)
                        usage_count_str = cast(str, usage_record["usage_count"])
                        usage_count = int(usage_count_str)

                        # Delete source if no longer used
                        if usage_count == 0:
                            delete_source_query = f"""
                            MATCH (s:Source {{id: '{source_id_str}'}})
                            DETACH DELETE s
                            RETURN true AS source_deleted
                            """

                            await self._execute_cypher(
                                cypher_query=delete_source_query,
                                as_clause="as (source_deleted agtype)",
                                fetch_mode="row",
                            )

        # Check and delete identifiers that are no longer used
        if entity_data["identifier"]:
            identifier_value = entity_data["identifier"]["identifier"].value
            identifier_type = entity_data["identifier"]["identifier"].type

            # Check if identifier is still used by other entities
            # Note: We need to check after all relationships are deleted
            check_identifier_query = f"""
            MATCH (i:Identifier {{value: '{self._escape_cypher_string(identifier_value)}', type: '{self._escape_cypher_string(identifier_type)}'}})
            OPTIONAL MATCH (e:Entity)-[:HAS_IDENTIFIER]->(i)
            RETURN count(e) AS identifier_usage_count
            """

            record = await self._execute_cypher(
                cypher_query=check_identifier_query,
                as_clause="as (identifier_usage_count agtype)",
                fetch_mode="row",
            )

            if record:
                record = cast(asyncpg.Record, record)
                usage_count_str = cast(str, record["identifier_usage_count"])
                usage_count = int(usage_count_str)

                # If no longer used, delete the identifier
                if usage_count == 0:
                    delete_identifier_query = f"""
                    MATCH (i:Identifier {{value: '{self._escape_cypher_string(identifier_value)}', type: '{self._escape_cypher_string(identifier_type)}'}})
                    DETACH DELETE i
                    RETURN true AS identifier_deleted
                    """

                    await self._execute_cypher(
                        cypher_query=delete_identifier_query,
                        as_clause="as (identifier_deleted agtype)",
                        fetch_mode="row",
                    )

        return True

    @override
    async def add_fact_to_entity(
        self,
        entity_id: str,
        fact: Fact,
        source: Source,
        verb: str,
        confidence_score: float = 1.0,
    ) -> AddFactToEntityResult:
        """
        Add a fact to an entity with its source using an idempotent approach.

        This method creates or updates the fact, source, and relationships in the graph.
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
        # At this point we know fact_id is not None
        assert created_fact.fact_id is not None

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
        cypher_query = f"""
        MATCH (f:Fact {{fact_id: '{fact_id}'}})
        OPTIONAL MATCH (f)-[df:DERIVED_FROM]->(s:Source)
        RETURN {{
            fact: f,
            source: s
        }} AS result
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
        result_map = cast(dict[str, Any], json.loads(cleaned_result_str))

        # Extract fact properties
        fact_props = cast(dict[str, Any], result_map["fact"]["properties"])
        fact = Fact(
            name=fact_props["name"],
            type=fact_props["type"],
        )

        # Verify fact_id matches (should be computed by model validator)
        if fact.fact_id != fact_props["fact_id"]:
            return None

        # Extract source if it exists
        source = None
        source_data = result_map.get("source")
        if source_data:
            source_props = cast(dict[str, Any], source_data["properties"])
            source = Source(
                id=UUID(source_props["id"]),
                content=source_props["content"],
                timestamp=datetime.fromisoformat(source_props["timestamp"]),
            )

        return {
            "fact": fact,
            "source": source,
        }

    @override
    async def remove_fact_from_entity(self, entity_id: str, fact_id: str) -> bool:
        """
        Remove a fact from an entity.

        Deletes all HAS_FACT relationships between the entity and fact.
        If the fact is only used by this entity, also deletes the fact itself.
        If the source is only used by this fact, also deletes the source.

        Returns:
            True if the relationship was deleted, False if not found.
        """
        # 1. Check if the relationship exists
        check_query = f"""
        MATCH (e:Entity {{id: '{entity_id}'}})-[hf:HAS_FACT]->(f:Fact {{fact_id: '{fact_id}'}})
        RETURN count(hf) AS relationship_count
        """

        record = await self._execute_cypher(
            cypher_query=check_query,
            as_clause="as (relationship_count agtype)",
            fetch_mode="row",
        )

        if not record:
            return False

        record = cast(asyncpg.Record, record)
        relationship_count_str = cast(str, record["relationship_count"])
        relationship_count = int(relationship_count_str)

        if relationship_count == 0:
            return False

        # 2. Count how many entities use this fact
        count_usage_query = f"""
        MATCH (e:Entity)-[:HAS_FACT]->(f:Fact {{fact_id: '{fact_id}'}})
        RETURN count(e) AS entity_count
        """

        usage_record = await self._execute_cypher(
            cypher_query=count_usage_query,
            as_clause="as (entity_count agtype)",
            fetch_mode="row",
        )

        usage_record = cast(asyncpg.Record, usage_record)
        entity_count_str = cast(str, usage_record["entity_count"])
        entity_count = int(entity_count_str)

        # 3. Get the source ID before deleting
        source_query = f"""
        MATCH (f:Fact {{fact_id: '{fact_id}'}})-[:DERIVED_FROM]->(s:Source)
        RETURN s.id AS source_id
        """

        source_record = await self._execute_cypher(
            cypher_query=source_query,
            as_clause="as (source_id agtype)",
            fetch_mode="row",
        )

        source_id_str = None
        if source_record:
            source_record = cast(asyncpg.Record, source_record)
            source_id_str = cast(str, source_record["source_id"])
            # Check if source_id is not null
            if source_id_str == "null":
                source_id_str = None

        # 4. Delete all HAS_FACT relationships between entity and fact
        delete_relationships_query = f"""
        MATCH (e:Entity {{id: '{entity_id}'}})-[hf:HAS_FACT]->(f:Fact {{fact_id: '{fact_id}'}})
        DELETE hf
        RETURN count(hf) AS deleted_count
        """

        _ = await self._execute_cypher(
            cypher_query=delete_relationships_query,
            as_clause="as (deleted_count agtype)",
            fetch_mode="row",
        )

        # 5. If fact was only used by this entity, delete the fact
        should_delete_fact = entity_count == relationship_count

        if should_delete_fact:
            delete_fact_query = f"""
            MATCH (f:Fact {{fact_id: '{fact_id}'}})
            DETACH DELETE f
            RETURN true AS fact_deleted
            """

            _ = await self._execute_cypher(
                cypher_query=delete_fact_query,
                as_clause="as (fact_deleted agtype)",
                fetch_mode="row",
            )

            # 6. If we deleted the fact and it had a source, check if source should be deleted
            if source_id_str:
                check_source_usage_query = f"""
                MATCH (s:Source {{id: '{source_id_str}'}})
                OPTIONAL MATCH (f:Fact)-[:DERIVED_FROM]->(s)
                RETURN count(f) AS fact_count
                """

                source_usage_record = await self._execute_cypher(
                    cypher_query=check_source_usage_query,
                    as_clause="as (fact_count agtype)",
                    fetch_mode="row",
                )

                if source_usage_record:
                    source_usage_record = cast(asyncpg.Record, source_usage_record)
                    fact_count_str = cast(str, source_usage_record["fact_count"])
                    fact_count = int(fact_count_str)

                    # If no facts reference this source, delete it
                    if fact_count == 0:
                        delete_source_query = f"""
                        MATCH (s:Source {{id: '{source_id_str}'}})
                        DETACH DELETE s
                        RETURN true AS source_deleted
                        """

                        _ = await self._execute_cypher(
                            cypher_query=delete_source_query,
                            as_clause="as (source_deleted agtype)",
                            fetch_mode="row",
                        )

        return True
