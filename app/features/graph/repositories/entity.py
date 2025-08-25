"""Entity repository for database operations."""

from typing import Any
from uuid import UUID

from app.db.graph import GraphDB
from app.features.graph.models import Entity, HasIdentifier, Identifier


class EntityRepository:
    """Handles all entity-related database operations."""

    def __init__(self, db: GraphDB):
        self.db = db

    async def create_entity(
        self, entity: Entity, identifier: Identifier, relationship: HasIdentifier
    ) -> bool:
        """Create a new entity with identifier in the database."""
        query = """
        MERGE (i:Identifier {value: $identifier_value})
        ON CREATE SET i.type = $identifier_type
        CREATE (e:Entity {
            id: $entity_id,
            created_at: $created_at,
            metadata: $metadata
        })
        CREATE (e)-[:HAS_IDENTIFIER {
            is_primary: $is_primary,
            created_at: $relationship_created_at
        }]->(i)
        RETURN e.id AS entityId, i.value AS identifierValue
        """

        parameters = {
            "entity_id": str(entity.id),
            "created_at": entity.created_at.isoformat(),
            "metadata": entity.metadata,
            "identifier_value": identifier.value,
            "identifier_type": identifier.type,
            "is_primary": relationship.is_primary,
            "relationship_created_at": relationship.created_at.isoformat(),
        }

        result = await self.db.execute_query(query, parameters)
        return result.get("success", False)

    async def find_entity_by_id(self, entity_id: UUID) -> dict[str, Any] | None:
        """Find entity by ID with all its identifiers and facts."""
        query = """
        MATCH (e:Entity {id: $entity_id})
        OPTIONAL MATCH (e)-[hi:HAS_IDENTIFIER]->(i:Identifier)
        OPTIONAL MATCH (e)-[hf:HAS_FACT]->(f:Fact)
        OPTIONAL MATCH (f)-[:DERIVED_FROM]->(s:Source)
        RETURN e, collect(i) as identifiers, collect(f) as facts,
               collect(s) as sources, collect(hf) as fact_relationships
        """

        result = await self.db.execute_query(query, {"entity_id": str(entity_id)})
        return result if result.get("data") else None

    async def find_entities(
        self, identifier_value: str | None, identifier_type: str | None, limit: int
    ) -> list[dict[str, Any]]:
        """Search for entities by identifier or get all entities."""
        if identifier_value:
            # Search by specific identifier
            query = f"""
            MATCH (e:Entity)-[:HAS_IDENTIFIER]->(i:Identifier)
            WHERE i.value = $identifier_value
            {"AND i.type = $identifier_type" if identifier_type else ""}
            RETURN e, collect(i) as identifiers
            LIMIT $limit
            """

            parameters = {"identifier_value": identifier_value, "limit": limit}
            if identifier_type:
                parameters["identifier_type"] = identifier_type
        else:
            # Get all entities
            query = """
            MATCH (e:Entity)
            OPTIONAL MATCH (e)-[:HAS_IDENTIFIER]->(i:Identifier)
            RETURN e, collect(i) as identifiers
            LIMIT $limit
            """
            parameters = {"limit": limit}

        result = await self.db.execute_query(query, parameters)
        return result.get("data", [])
