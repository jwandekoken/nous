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
        RETURN e, i, r
        """

        parameters = {
            "identifier_value": identifier.value,
            "identifier_type": identifier.type,
            "is_primary": relationship.is_primary,
        }

        result: dict[str, Any] = await self.db.execute_query(query, parameters)

        # Parse the results and construct the return objects
        rows = result.get("rows")
        if not rows or len(rows) == 0:
            raise RuntimeError("Failed to create entity - no data returned")

        # Extract data from the Cypher query result
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
            value=str(identifier_data["value"]), type=str(identifier_data["type"])
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

    async def find_entity_by_id(self, entity_id: UUID) -> dict[str, Any] | None:  # type: ignore[return]
        """Find entity by ID with all its identifiers and facts."""
        query = """
        MATCH (e:Entity {id: $entity_id})
        OPTIONAL MATCH (e)-[hi:HAS_IDENTIFIER]->(i:Identifier)
        OPTIONAL MATCH (e)-[hf:HAS_FACT]->(f:Fact)
        OPTIONAL MATCH (f)-[:DERIVED_FROM]->(s:Source)
        RETURN e, collect(i) as identifiers, collect(f) as facts,
               collect(s) as sources, collect(hf) as fact_relationships
        """

        result: dict[str, Any] = await self.db.execute_query(
            query, {"entity_id": str(entity_id)}
        )  # type: ignore[assignment]
        return result if result.get("data") else None

    async def find_entities(
        self, identifier_value: str | None, identifier_type: str | None, limit: int
    ) -> list[dict[str, Any]]:  # type: ignore[return]
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

        result: dict[str, Any] = await self.db.execute_query(query, parameters)  # type: ignore[assignment]
        return result.get("data", [])  # type: ignore[return-value]

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

        result: dict[str, Any] = await self.db.execute_query(
            query, {"entity_id": str(entity_id)}
        )  # type: ignore[assignment]
        # Check if any entities were actually deleted
        rows = result.get("rows", [])  # type: ignore[assignment]
        return (
            rows
            and len(rows) > 0  # type: ignore[arg-type]
            and rows[0].get("deleted_entities", 0) > 0  # type: ignore[index]
        )
