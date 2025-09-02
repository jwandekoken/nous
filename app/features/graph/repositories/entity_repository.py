"""Entity repository for database operations."""

from typing import Any, TypedDict
from uuid import UUID

from app.db.graph import GraphDB
from app.features.graph.models import Entity, HasIdentifier, Identifier


class CreateEntityResult(TypedDict):
    """Result of creating a new entity with its identifier and relationship."""

    entity: Entity
    identifier: Identifier
    relationship: HasIdentifier


class EntityRepository:
    """Handles all entity-related database operations."""

    def __init__(self, db: GraphDB):
        self.db: GraphDB = db

    async def create_entity(
        self, entity: Entity, identifier: Identifier, relationship: HasIdentifier
    ) -> CreateEntityResult:
        """Create a new entity with identifier in the database."""
        created_at_str = entity.to_db_timestamp()
        relationship_created_at_str = relationship.to_db_timestamp()

        # Get metadata formatted for KuzuDB MAP format
        metadata_clause = entity.format_metadata_for_db()

        query = f"""
        MERGE (i:Identifier {{value: $identifier_value}})
        ON CREATE SET i.type = $identifier_type
        MERGE (e:Entity {{id: uuid($entity_id)}})
        ON CREATE SET
            e.created_at = timestamp($created_at_str),
            e.metadata = {metadata_clause}
        MERGE (e)-[r:HAS_IDENTIFIER]->(i)
        ON CREATE SET
            r.is_primary = $is_primary,
            r.created_at = timestamp($relationship_created_at_str)
        RETURN e, i, r
        """

        parameters = {
            "identifier_value": identifier.value,
            "identifier_type": identifier.type,
            "entity_id": str(entity.id),
            "created_at_str": created_at_str,
            "is_primary": relationship.is_primary,
            "relationship_created_at_str": relationship_created_at_str,
        }

        result: dict[str, Any] = await self.db.execute_query(query, parameters)

        rows = result.get("rows")
        if not rows or len(rows) == 0:
            raise RuntimeError("Failed to create entity - no data returned")

        # KuzuDB returns results as dicts with keys "e", "i", "r"
        row_data = rows[0]
        entity_data = row_data["e"]
        identifier_data = row_data["i"]
        relationship_data = row_data["r"]

        # Extract entity data - KuzuDB returns nodes as dicts
        created_entity = Entity(
            id=UUID(str(entity_data["id"])),
            created_at=entity.created_at,  # Use the original created_at since timestamps might be different
            metadata=entity.metadata,  # Use original metadata
        )

        # Extract identifier data
        created_identifier = Identifier(
            value=str(identifier_data["value"]),
            type=str(identifier_data["type"]),
        )

        # Extract relationship data
        created_relationship = HasIdentifier(
            from_entity_id=UUID(str(entity_data["id"])),
            to_identifier_value=str(identifier_data["value"]),
            is_primary=bool(relationship_data["is_primary"]),
            created_at=relationship.created_at,  # Use original created_at
        )

        return {
            "entity": created_entity,
            "identifier": created_identifier,
            "relationship": created_relationship,
        }

    async def find_entity_by_id(self, entity_id: UUID) -> dict[str, Any] | None:
        """Find entity by ID with all its identifiers and facts."""
        query = f"""
        MATCH (e:Entity {{id: uuid('{entity_id}')}})
        OPTIONAL MATCH (e)-[hi:HAS_IDENTIFIER]->(i:Identifier)
        OPTIONAL MATCH (e)-[hf:HAS_FACT]->(f:Fact)
        OPTIONAL MATCH (f)-[:DERIVED_FROM]->(s:Source)
        RETURN e, collect(i) as identifiers, collect(f) as facts,
               collect(s) as sources, collect(hf) as fact_relationships
        """

        result: dict[str, Any] = await self.db.execute_query(query)
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

        result: dict[str, Any] = await self.db.execute_query(query, parameters)
        return result.get("data", [])

    async def delete_entity_by_id(self, entity_id: UUID) -> bool:
        """Delete an entity and all its relationships from the database.

        This method performs a cascade delete:
        1. Removes all HAS_IDENTIFIER relationships
        2. Removes the entity node
        3. Also removes identifiers that are no longer used by other entities

        Args:
            entity_id: UUID of the entity to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        query = f"""
        MATCH (e:Entity {{id: uuid('{entity_id}')}})
        OPTIONAL MATCH (e)-[r:HAS_IDENTIFIER]->(i:Identifier)
        WITH e, r, i, count(e) as entity_count
        OPTIONAL MATCH (other_e:Entity)-[other_r:HAS_IDENTIFIER]->(i)
        WHERE other_e <> e
        WITH e, r, i, entity_count, count(other_r) as other_rel_count
        DELETE r, e
        WITH i, entity_count, other_rel_count
        WHERE other_rel_count = 0
        DELETE i
        RETURN entity_count as deleted_entities
        """

        result: dict[str, Any] = await self.db.execute_query(query)

        # Check if any entities were actually deleted
        rows = result.get("rows", [])
        if not rows:
            # No entity was found to delete
            return False
        return rows[0].get("deleted_entities", 0) > 0
