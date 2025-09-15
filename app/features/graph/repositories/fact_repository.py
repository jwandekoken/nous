"""Fact repository for database operations."""

from typing import Any
from uuid import UUID

from app.db.arcadedb import GraphDB
from app.features.graph.models import Fact, HasFact, Source


class FactRepository:
    """Handles all fact-related database operations."""

    def __init__(self, db: GraphDB):
        self.db = db

    async def add_fact_to_entity(
        self, entity_id: UUID, fact: Fact, source: Source, has_fact: HasFact
    ) -> bool:
        """Add a fact to an existing entity with source information."""
        query = """
        MATCH (e:Entity {id: $entity_id})
        CREATE (f:Fact {
            fact_id: $fact_id,
            name: $fact_name,
            type: $fact_type
        })
        CREATE (s:Source {
            id: $source_id,
            content: $source_content,
            timestamp: $source_timestamp
        })
        CREATE (e)-[:HAS_FACT {
            verb: $verb,
            confidence_score: $confidence_score,
            created_at: $has_fact_created_at
        }]->(f)
        CREATE (f)-[:DERIVED_FROM]->(s)
        RETURN f, s
        """

        parameters = {
            "entity_id": str(entity_id),
            "fact_id": fact.fact_id or "",
            "fact_name": fact.name,
            "fact_type": fact.type,
            "source_id": str(source.id),
            "source_content": source.content,
            "source_timestamp": source.timestamp.isoformat()
            if source.timestamp
            else "",
            "verb": has_fact.verb,
            "confidence_score": has_fact.confidence_score,
            "has_fact_created_at": has_fact.created_at.isoformat(),
        }

        result = await self.db.execute_query(query, parameters)
        return result.get("success", False)

    async def find_fact_by_id(self, fact_id: str) -> dict[str, Any] | None:
        """Get a fact with its source information."""
        query = """
        MATCH (f:Fact {fact_id: $fact_id})
        OPTIONAL MATCH (f)-[:DERIVED_FROM]->(s:Source)
        OPTIONAL MATCH (e:Entity)-[:HAS_FACT]->(f)
        RETURN f, s, collect(e) as entities
        """

        result = await self.db.execute_query(query, {"fact_id": fact_id})
        return result if result.get("data") else None
