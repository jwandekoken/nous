"""Entity repository for database operations."""

from typing import Any
from uuid import UUID

from app.db.graph import GraphDB
from app.features.graph.models import Entity, HasIdentifier, Identifier


class EntityRepository:
    """Handles all entity-related database operations."""

    def __init__(self, db: GraphDB):
        self.db: GraphDB = db

    async def create_entity(
        self, entity: Entity, identifier: Identifier, relationship: HasIdentifier
    ) -> bool:
        """Create a new entity with identifier in the database."""
        created_at_str = entity.created_at.strftime("%Y-%m-%d %H:%M:%S")
        relationship_created_at_str = relationship.created_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Convert metadata dict to KuzuDB MAP format
        metadata_clause = ""
        if entity.metadata:
            # Convert dict to MAP using map([keys], [values]) syntax
            keys = list(entity.metadata.keys())
            values = list(entity.metadata.values())
            keys_str = ", ".join([f"'{k}'" for k in keys])
            values_str = ", ".join([f"'{v}'" for v in values])
            metadata_clause = f"e.metadata = map([{keys_str}], [{values_str}])"
        else:
            metadata_clause = "e.metadata = map([], [])"

        query = f"""
        MERGE (i:Identifier {{value: $identifier_value}})
        ON CREATE SET i.type = $identifier_type
        MERGE (e:Entity {{id: uuid('{entity.id}')}})
        ON CREATE SET
            e.created_at = timestamp('{created_at_str}')
            {"," + metadata_clause if metadata_clause else ""}
        MERGE (e)-[r:HAS_IDENTIFIER]->(i)
        ON CREATE SET
            r.is_primary = $is_primary,
            r.created_at = timestamp('{relationship_created_at_str}')
        RETURN e.id AS entityId, i.value AS identifierValue
        """

        parameters = {
            "identifier_value": identifier.value,
            "identifier_type": identifier.type,
            "is_primary": relationship.is_primary,
        }

        result = await self.db.execute_query(query, parameters)
        # Query is successful if we get a response with rows (no HTTP error occurred)
        return len(result.get("rows", [])) > 0

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

    async def delete_entity_by_id(self, entity_id: UUID) -> bool:
        """Delete an entity and all its relationships from the database.

        This method performs a cascade delete:
        1. Removes all HAS_IDENTIFIER relationships
        2. Removes the entity node
        3. Note: Identifiers are kept as they might be shared with other entities

        Args:
            entity_id: UUID of the entity to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        query = """
        MATCH (e:Entity {id: $entity_id})
        OPTIONAL MATCH (e)-[r:HAS_IDENTIFIER]->(i:Identifier)
        DELETE r, e
        RETURN count(e) as deleted_entities
        """

        result = await self.db.execute_query(query, {"entity_id": str(entity_id)})
        # Check if any entities were actually deleted
        return (
            result.get("rows", [])
            and len(result["rows"]) > 0
            and result["rows"][0].get("deleted_entities", 0) > 0
        )
