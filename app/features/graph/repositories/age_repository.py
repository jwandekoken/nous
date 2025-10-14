"""PostgreSQL AGE implementation of the graph repository protocol."""

import json
from datetime import datetime
from typing import Any, cast, override
from uuid import UUID

import asyncpg  # type: ignore

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


def _parse_vertex_properties(props: dict[str, Any]) -> dict[str, Any]:
    """Parse vertex properties from AGE format."""
    parsed = props.copy()
    if "id" in parsed and "value" not in parsed:
        parsed["id"] = UUID(parsed["id"])
    if "created_at" in parsed:
        parsed["created_at"] = datetime.fromisoformat(parsed["created_at"])
    if "timestamp" in parsed:
        parsed["timestamp"] = datetime.fromisoformat(parsed["timestamp"])
    if "metadata" in parsed and isinstance(parsed["metadata"], str):
        try:
            parsed["metadata"] = json.loads(parsed["metadata"])
        except json.JSONDecodeError:
            parsed["metadata"] = {}
    return parsed


def _parse_edge_properties(props: dict[str, Any]) -> dict[str, Any]:
    """Parse edge properties from AGE format."""
    parsed = props.copy()
    if "created_at" in parsed:
        parsed["created_at"] = datetime.fromisoformat(parsed["created_at"])
    return parsed


class AgeRepository(GraphRepository):
    """PostgreSQL AGE implementation of the graph repository."""

    pool: asyncpg.Pool
    graph_name: str

    def __init__(self, pool: asyncpg.Pool):
        """Initialize the repository with a database connection pool."""
        self.pool = pool
        self.graph_name = get_settings().age_graph_name

    async def _execute_cypher(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Execute a Cypher query and returns results as a list of dicts."""
        cypher_call = f"""
            SELECT * FROM ag_catalog.cypher(
                '{self.graph_name}',
                $$ {query} $$,
                $1
            ) as (v agtype)
        """
        final_query = f"SELECT v::jsonb FROM ({cypher_call}) as result"

        async with self.pool.acquire() as conn:
            conn = cast(asyncpg.Connection, conn)
            await conn.execute("LOAD 'age';")
            await conn.execute("SET search_path = ag_catalog, '$user', public;")
            params_json = json.dumps(kwargs, default=str)
            records = await conn.fetch(final_query, params_json)
            return [json.loads(record["v"]) for record in records]

    @override
    async def create_entity(
        self, entity: Entity, identifier: Identifier, relationship: HasIdentifier
    ) -> CreateEntityResult:
        """Create a new entity with an identifier. This method is idempotent."""
        existing_entity = await self.find_entity_by_identifier(
            identifier.value, identifier.type
        )
        if existing_entity:
            return {
                "entity": existing_entity["entity"],
                "identifier": existing_entity["identifier"]["identifier"],
                "relationship": existing_entity["identifier"]["relationship"],
            }

        query = """
        MERGE (i:Identifier {value: $value, type: $type})
        CREATE (e:Entity {id: $entity_id, created_at: $created_at, metadata: $metadata})
        CREATE (e)-[r:HAS_IDENTIFIER {is_primary: $is_primary, created_at: $rel_created_at}]->(i)
        RETURN {
            'entity': e,
            'identifier': i,
            'relationship': r
        }
        """
        params = {
            "value": identifier.value,
            "type": identifier.type,
            "entity_id": str(entity.id),
            "created_at": entity.created_at.isoformat(),
            "metadata": json.dumps(entity.metadata) if entity.metadata else "{}",
            "is_primary": relationship.is_primary,
            "rel_created_at": relationship.created_at.isoformat(),
        }

        records = await self._execute_cypher(query, **params)
        if not records:
            raise RuntimeError("Failed to create entity in AGE repository.")
        data = records[0]
        entity_data = data["entity"]
        created_entity = Entity(**_parse_vertex_properties(entity_data["properties"]))
        identifier_data = data["identifier"]
        created_identifier = Identifier(
            **_parse_vertex_properties(identifier_data["properties"])
        )
        rel_data = data["relationship"]
        created_relationship = HasIdentifier(
            from_entity_id=created_entity.id,
            to_identifier_value=created_identifier.value,
            **_parse_edge_properties(rel_data["properties"]),
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
        query = """
        MATCH (i:Identifier {value: $value, type: $type})<-[r:HAS_IDENTIFIER]-(e:Entity)
        OPTIONAL MATCH (e)-[hf:HAS_FACT]->(f:Fact)
        OPTIONAL MATCH (f)-[df:DERIVED_FROM]->(s:Source)
        RETURN {
            entity: e,
            identifier: i,
            relationship: r,
            facts_with_sources: collect(DISTINCT {
                fact: f,
                relationship: hf,
                source: s,
                derived_from: df
            })
        }
        """

        params = {"value": identifier_value, "type": identifier_type}
        records = await self._execute_cypher(query, **params)

        if not records:
            return None

        data = records[0]

        entity_data = data["entity"]
        entity = Entity(**_parse_vertex_properties(entity_data["properties"]))

        identifier_data = data["identifier"]
        identifier = Identifier(
            **_parse_vertex_properties(identifier_data["properties"])
        )

        rel_data = data["relationship"]
        has_identifier_rel = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=identifier.value,
            **_parse_edge_properties(rel_data["properties"]),
        )

        facts_with_sources: list[FactWithSource] = []
        if data["facts_with_sources"] and data["facts_with_sources"][0].get("fact"):
            for item in data["facts_with_sources"]:
                fact_data = item["fact"]
                fact = Fact(**_parse_vertex_properties(fact_data["properties"]))

                has_fact_data = item["relationship"]

                if not fact.fact_id:
                    raise ValueError("Fact ID is missing after retrieval.")

                has_fact_rel = HasFact(
                    from_entity_id=entity.id,
                    to_fact_id=fact.fact_id,
                    **_parse_edge_properties(has_fact_data["properties"]),
                )

                source = None
                if item.get("source"):
                    source_data = item["source"]
                    source = Source(
                        **_parse_vertex_properties(source_data["properties"])
                    )

                facts_with_sources.append(
                    {
                        "fact": fact,
                        "relationship": has_fact_rel,
                        "source": source,
                    }
                )

        return {
            "entity": entity,
            "identifier": {
                "identifier": identifier,
                "relationship": has_identifier_rel,
            },
            "facts_with_sources": facts_with_sources,
        }

    @override
    async def find_entity_by_id(self, entity_id: str) -> FindEntityByIdResult | None:
        """Find an entity by its ID."""
        query = """
        MATCH (e:Entity {id: $entity_id})
        OPTIONAL MATCH (e)-[r:HAS_IDENTIFIER]->(i:Identifier)
        OPTIONAL MATCH (e)-[hf:HAS_FACT]->(f:Fact)
        OPTIONAL MATCH (f)-[df:DERIVED_FROM]->(s:Source)
        RETURN {
            entity: e,
            identifiers_with_rels: collect(DISTINCT {identifier: i, relationship: r}),
            facts_with_sources: collect(DISTINCT {
                fact: f,
                relationship: hf,
                source: s,
                derived_from: df
            })
        }
        """
        params = {"entity_id": entity_id}
        records = await self._execute_cypher(query, **params)

        if not records or not records[0].get("entity"):
            return None

        data = records[0]

        entity_data = data["entity"]
        entity = Entity(**_parse_vertex_properties(entity_data["properties"]))

        primary_identifier_with_rel: IdentifierWithRelationship | None = None
        if data["identifiers_with_rels"] and data["identifiers_with_rels"][0].get(
            "identifier"
        ):
            # Find the primary identifier, or take the first one.
            raw_identifiers = data["identifiers_with_rels"]
            primary_raw = next(
                (
                    item
                    for item in raw_identifiers
                    if item["relationship"]["properties"].get("is_primary")
                ),
                raw_identifiers[0],
            )

            identifier = Identifier(
                **_parse_vertex_properties(primary_raw["identifier"]["properties"])
            )
            has_identifier_rel = HasIdentifier(
                from_entity_id=entity.id,
                to_identifier_value=identifier.value,
                **_parse_edge_properties(primary_raw["relationship"]["properties"]),
            )
            primary_identifier_with_rel = {
                "identifier": identifier,
                "relationship": has_identifier_rel,
            }

        facts_with_sources: list[FactWithSource] = []
        if data["facts_with_sources"] and data["facts_with_sources"][0].get("fact"):
            for item in data["facts_with_sources"]:
                fact = Fact(**_parse_vertex_properties(item["fact"]["properties"]))
                if not fact.fact_id:
                    raise ValueError("Fact ID is missing after retrieval.")
                has_fact_rel = HasFact(
                    from_entity_id=entity.id,
                    to_fact_id=fact.fact_id,
                    **_parse_edge_properties(item["relationship"]["properties"]),
                )
                source = None
                if item.get("source"):
                    source = Source(
                        **_parse_vertex_properties(item["source"]["properties"])
                    )
                facts_with_sources.append(
                    {
                        "fact": fact,
                        "relationship": has_fact_rel,
                        "source": source,
                    }
                )

        return {
            "entity": entity,
            "identifier": primary_identifier_with_rel,
            "facts_with_sources": facts_with_sources,
        }

    @override
    async def delete_entity_by_id(self, entity_id: str) -> bool:
        """Delete an entity by its ID."""
        # This operation is not atomic, but it's the most reliable way to
        # determine if a deletion occurred with AGE's current capabilities.
        find_query = "MATCH (e:Entity {id: $entity_id}) RETURN count(e) as count"
        find_result = await self._execute_cypher(find_query, entity_id=entity_id)

        if not find_result or find_result[0]["count"] == 0:
            return False

        delete_query = "MATCH (e:Entity {id: $entity_id}) DETACH DELETE e"
        await self._execute_cypher(delete_query, entity_id=entity_id)
        return True

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
        query = """
        MATCH (e:Entity {id: $entity_id})
        MERGE (f:Fact {fact_id: $fact_id})
            ON CREATE SET f.name = $fact_name, f.type = $fact_type
        MERGE (s:Source {id: $source_id})
            ON CREATE SET s.content = $source_content, s.timestamp = $source_timestamp
        MERGE (e)-[hf:HAS_FACT {verb: $verb}]->(f)
            ON CREATE SET hf.confidence_score = $confidence_score, hf.created_at = $created_at
        MERGE (f)-[df:DERIVED_FROM]->(s)
            ON CREATE SET df.created_at = $created_at
        RETURN {
            fact: f,
            source: s,
            has_fact_relationship: hf,
            derived_from_relationship: df
        }
        """

        now = datetime.now()
        params = {
            "entity_id": entity_id,
            "fact_id": fact.fact_id,
            "fact_name": fact.name,
            "fact_type": fact.type,
            "source_id": str(source.id),
            "source_content": source.content,
            "source_timestamp": source.timestamp.isoformat(),
            "verb": verb,
            "confidence_score": confidence_score,
            "created_at": now.isoformat(),
        }

        records = await self._execute_cypher(query, **params)
        data = records[0]

        created_fact = Fact(**_parse_vertex_properties(data["fact"]["properties"]))
        created_source = Source(
            **_parse_vertex_properties(data["source"]["properties"])
        )
        if not created_fact.fact_id:
            raise ValueError("Fact ID is missing after creation.")
        has_fact_rel = HasFact(
            from_entity_id=UUID(entity_id),
            to_fact_id=created_fact.fact_id,
            **_parse_edge_properties(data["has_fact_relationship"]["properties"]),
        )
        derived_from_rel = DerivedFrom(
            from_fact_id=created_fact.fact_id,
            to_source_id=created_source.id,
            **_parse_edge_properties(data["derived_from_relationship"]["properties"]),
        )

        return {
            "fact": created_fact,
            "source": created_source,
            "has_fact_relationship": has_fact_rel,
            "derived_from_relationship": derived_from_rel,
        }

    @override
    async def find_fact_by_id(self, fact_id: str) -> FactWithOptionalSource | None:
        """Find a fact by its ID."""
        query = """
        MATCH (f:Fact {fact_id: $fact_id})
        OPTIONAL MATCH (f)-[:DERIVED_FROM]->(s:Source)
        RETURN {
            fact: f,
            source: s
        }
        """
        params = {"fact_id": fact_id}
        records = await self._execute_cypher(query, **params)

        if not records or not records[0].get("fact"):
            return None

        data = records[0]

        fact = Fact(**_parse_vertex_properties(data["fact"]["properties"]))
        source = None
        if data.get("source"):
            source = Source(**_parse_vertex_properties(data["source"]["properties"]))

        return {"fact": fact, "source": source}
