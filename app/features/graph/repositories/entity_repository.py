"""Entity repository for database operations."""

from typing import TypedDict

from app.db.arcadedb import GraphDB, get_database_name
from app.features.graph.models import (
    Entity,
    Fact,
    HasFact,
    HasIdentifier,
    Identifier,
    Source,
)


class CreateEntityResult(TypedDict):
    """Result of creating a new entity with its identifier and relationship."""

    entity: Entity
    identifier: Identifier
    relationship: HasIdentifier


class FactWithSource(TypedDict):
    """A fact with its associated source information."""

    fact: Fact
    source: Source | None
    relationship: HasFact


class EntityWithRelations(TypedDict):
    """Complete entity data with all its relationships and associated objects."""

    entity: Entity
    identifiers: list[Identifier]
    facts_with_sources: list[FactWithSource]


class EntityRepository:
    """Handles all entity-related database operations."""

    def __init__(self, db: GraphDB):
        self.db: GraphDB = db

    async def create_entity(
        self, entity: Entity, identifier: Identifier, relationship: HasIdentifier
    ) -> CreateEntityResult:
        """Create a new entity with identifier in the database using ArcadeDB SQL."""

        # Pass metadata as dictionary for MAP type in ArcadeDB
        metadata_dict = entity.metadata if entity.metadata else {}

        database_name = get_database_name()

        # Execute commands sequentially with proper error handling
        try:
            # Create entity vertex with parameterized query

            params = {
                "entity_id": str(entity.id),
                "created_at": entity.created_at.isoformat(),
                "metadata": metadata_dict,
                "identifier_value": identifier.value,
                "identifier_type": identifier.type,
            }

            # Use sqlscript with transaction for the CREATE VERTEX operations
            transaction_script = """
            BEGIN;
            CREATE VERTEX Entity
            SET id = :entity_id,
                created_at = :created_at,
                metadata = :metadata;
            CREATE VERTEX Identifier
            SET value = :identifier_value,
                type = :identifier_type;
            COMMIT;
            """

            created_entity_result = await self.db.execute_command(
                transaction_script,
                database_name,
                parameters=params,
                language="sqlscript",
            )
            print("created_entity_result: ", created_entity_result)

            # Check if entity was created successfully
            if not created_entity_result.get("result"):
                raise RuntimeError("Failed to create entity")

            # For transactions, the result contains commit info, not the created vertex data
            # So we use the original entity data since the transaction succeeded
            result_list = created_entity_result["result"]
            if not result_list:
                raise RuntimeError("No transaction result")

            # Check if the transaction committed successfully
            commit_result = (
                result_list[0] if isinstance(result_list, list) else result_list
            )
            if commit_result.get("operation") != "commit":
                raise RuntimeError("Transaction did not commit successfully")

            # Use the original entity data since transaction succeeded
            created_entity = Entity(
                id=entity.id,
                created_at=entity.created_at,
                metadata=entity.metadata,
            )

            # Return mock data for identifier and relationship (since we're focusing on entity creation)
            return {
                "entity": created_entity,
                "identifier": identifier,  # Return the original identifier
                "relationship": relationship,  # Return the original relationship
            }

        except Exception as e:
            # If any command fails, raise an error
            raise RuntimeError(f"Failed to create entity: {e}")

    # async def find_entity_by_id(self, entity_id: UUID) -> EntityWithRelations | None:
    #     """Find entity by ID with all its identifiers and facts using ArcadeDB SQL.

    #     Args:
    #         entity_id: UUID of the entity to find

    #     Returns:
    #         Complete entity data with all relationships, or None if not found
    #     """
    #     # Query to get entity with identifiers
    #     entity_query = f"""
    #     SELECT
    #         e.id as entity_id, e.created_at as entity_created_at, e.metadata as entity_metadata,
    #         i.value as identifier_value, i.type as identifier_type,
    #         hi.is_primary as relationship_is_primary, hi.created_at as relationship_created_at
    #     FROM Entity e
    #     LEFT JOIN HAS_IDENTIFIER hi ON e.@rid = hi.out
    #     LEFT JOIN Identifier i ON i.@rid = hi.in
    #     WHERE e.id = '{str(entity_id)}'
    #     """

    #     database_name = get_database_name()
    #     result: dict[str, Any] = await self.db.execute_query(
    #         entity_query, database_name
    #     )

    #     # Parse ArcadeDB result format
    #     if "result" not in result or not result["result"]:
    #         return None

    #     rows = result["result"]
    #     if not rows:
    #         return None

    #     # Extract entity data from first row
    #     first_row = rows[0] if isinstance(rows, list) else rows
    #     entity = Entity(
    #         id=UUID(str(first_row["entity_id"])),
    #         created_at=first_row["entity_created_at"],  # Database timestamp
    #         metadata=first_row.get("entity_metadata", {}),
    #     )

    #     # Extract identifiers from all rows
    #     identifiers = []
    #     for row in rows:
    #         if row.get("identifier_value"):  # Only if identifier exists
    #             identifiers.append(
    #                 Identifier(
    #                     value=str(row["identifier_value"]),
    #                     type=str(row["identifier_type"]),
    #                 )
    #             )

    #     # Query to get facts and sources
    #     facts_query = f"""
    #     SELECT
    #         f.name as fact_name, f.type as fact_type,
    #         hf.verb as relationship_verb, hf.confidence_score as relationship_confidence,
    #         hf.created_at as relationship_created_at,
    #         s.id as source_id, s.content as source_content, s.timestamp as source_timestamp
    #     FROM Entity e
    #     JOIN HAS_FACT hf ON e.@rid = hf.out
    #     JOIN Fact f ON f.@rid = hf.in
    #     LEFT JOIN DERIVED_FROM df ON f.@rid = df.out
    #     LEFT JOIN Source s ON s.@rid = df.in
    #     WHERE e.id = '{str(entity_id)}'
    #     """

    #     facts_result: dict[str, Any] = await self.db.execute_query(
    #         facts_query, database_name
    #     )

    #     facts_with_sources = []
    #     if facts_result.get("result"):
    #         facts_rows = facts_result["result"]
    #         for row in facts_rows:
    #             fact = Fact(
    #                 name=str(row["fact_name"]),
    #                 type=str(row["fact_type"]),
    #             )

    #             relationship = HasFact(
    #                 from_entity_id=entity_id,
    #                 to_fact_id=fact.fact_id or "",
    #                 verb=str(row.get("relationship_verb", "")),
    #                 confidence_score=float(row.get("relationship_confidence", 1.0)),
    #                 created_at=row.get("relationship_created_at"),
    #             )

    #             # Extract source if exists
    #             source = None
    #             if row.get("source_id"):
    #                 source = Source(
    #                     id=UUID(str(row["source_id"])),
    #                     content=str(row["source_content"]),
    #                     timestamp=row["source_timestamp"],
    #                 )

    #             facts_with_sources.append(
    #                 FactWithSource(
    #                     fact=fact,
    #                     source=source,
    #                     relationship=relationship,
    #                 )
    #             )

    #     return EntityWithRelations(
    #         entity=entity,
    #         identifiers=identifiers,
    #         facts_with_sources=facts_with_sources,
    #     )

    # async def find_entities(
    #     self, identifier_value: str | None, identifier_type: str | None, limit: int
    # ) -> list[dict[str, Any]]:
    #     """Search for entities by identifier or get all entities using ArcadeDB SQL."""

    #     if identifier_value:
    #         # Search by specific identifier
    #         type_condition = (
    #             f" AND i.type = '{identifier_type}'" if identifier_type else ""
    #         )
    #         query = f"""
    #         SELECT
    #             e.id as entity_id, e.created_at as entity_created_at, e.metadata as entity_metadata,
    #             i.value as identifier_value, i.type as identifier_type
    #         FROM Entity e
    #         JOIN HAS_IDENTIFIER hi ON e.@rid = hi.out
    #         JOIN Identifier i ON i.@rid = hi.in
    #         WHERE i.value = '{identifier_value}'{type_condition}
    #         LIMIT {limit}
    #         """
    #     else:
    #         # Get all entities
    #         query = f"""
    #         SELECT
    #             e.id as entity_id, e.created_at as entity_created_at, e.metadata as entity_metadata,
    #             i.value as identifier_value, i.type as identifier_type
    #         FROM Entity e
    #         LEFT JOIN HAS_IDENTIFIER hi ON e.@rid = hi.out
    #         LEFT JOIN Identifier i ON i.@rid = hi.in
    #         LIMIT {limit}
    #         """

    #     database_name = get_database_name()
    #     result: dict[str, Any] = await self.db.execute_query(query, database_name)

    #     # Convert ArcadeDB result format to expected format
    #     if "result" not in result or not result["result"]:
    #         return []

    #     rows = result["result"]
    #     if not rows:
    #         return []

    #     # Group results by entity (since JOIN can create multiple rows per entity)
    #     entities_map: dict[str, dict[str, Any]] = {}

    #     for row in rows:
    #         entity_id = str(row["entity_id"])
    #         if entity_id not in entities_map:
    #             entities_map[entity_id] = {
    #                 "e": {
    #                     "id": row["entity_id"],
    #                     "created_at": row["entity_created_at"],
    #                     "metadata": row.get("entity_metadata", {}),
    #                 },
    #                 "identifiers": [],
    #             }

    #         # Add identifier if it exists
    #         if row.get("identifier_value"):
    #             entities_map[entity_id]["identifiers"].append(
    #                 {
    #                     "value": row["identifier_value"],
    #                     "type": row["identifier_type"],
    #                 }
    #             )

    #     return list(entities_map.values())

    # async def delete_entity_by_id(self, entity_id: UUID) -> bool:
    #     """Delete an entity and all its relationships from the database using ArcadeDB SQL.

    #     This method performs a cascade delete:
    #     1. Removes all HAS_IDENTIFIER relationships
    #     2. Removes the entity vertex
    #     3. Also removes identifiers that are no longer used by other entities

    #     Args:
    #         entity_id: UUID of the entity to delete

    #     Returns:
    #         bool: True if deletion was successful, False otherwise
    #     """

    #     # First check if entity exists
    #     check_query = f"""
    #     SELECT e.id as entity_id
    #     FROM Entity e
    #     WHERE e.id = '{str(entity_id)}'
    #     """

    #     database_name = get_database_name()
    #     check_result = await self.db.execute_query(check_query, database_name)

    #     # Parse ArcadeDB result format
    #     if "result" not in check_result or not check_result["result"]:
    #         return False

    #     rows = check_result["result"]
    #     if not rows:
    #         return False

    #     # Entity exists, now delete it
    #     try:
    #         # Delete HAS_IDENTIFIER edges connected to the entity
    #         delete_edges_query = f"""
    #         DELETE FROM HAS_IDENTIFIER
    #         WHERE out IN (SELECT @rid FROM Entity WHERE id = '{str(entity_id)}')
    #         """
    #         await self.db.execute_command(delete_edges_query, database_name)

    #         # Delete the entity vertex
    #         delete_entity_query = f"""
    #         DELETE FROM Entity
    #         WHERE id = '{str(entity_id)}'
    #         """
    #         await self.db.execute_command(delete_entity_query, database_name)

    #         # Delete orphaned identifiers (identifiers not connected to any entity)
    #         delete_orphaned_identifiers_query = """
    #         DELETE FROM Identifier
    #         WHERE @rid NOT IN (
    #             SELECT DISTINCT `in`
    #             FROM HAS_IDENTIFIER
    #         )
    #         """
    #         await self.db.execute_command(
    #             delete_orphaned_identifiers_query, database_name
    #         )

    #     except Exception as e:
    #         raise RuntimeError(f"Failed to delete entity: {e}")

    #     return True

    # async def clear_test_data(self) -> None:
    #     """Clear all test data from the database using ArcadeDB SQL.

    #     This method deletes all entities, identifiers, facts, and sources that were
    #     created during integration testing. It identifies test data by looking for
    #     entities with test-related metadata.

    #     Warning: This method is destructive and should only be used in test environments.
    #     """
    #     try:
    #         database_name = get_database_name()

    #         # Delete all HAS_IDENTIFIER edges connected to test entities
    #         delete_test_edges_query = """
    #         DELETE FROM HAS_IDENTIFIER
    #         WHERE out IN (
    #             SELECT @rid FROM Entity
    #             WHERE metadata CONTAINSKEY 'test_type'
    #         )
    #         """
    #         await self.db.execute_command(delete_test_edges_query, database_name)

    #         # Delete all test entities
    #         delete_test_entities_query = """
    #         DELETE FROM Entity
    #         WHERE metadata CONTAINSKEY 'test_type'
    #         """
    #         await self.db.execute_command(delete_test_entities_query, database_name)

    #         # Delete orphaned identifiers (not connected to any entity)
    #         delete_orphaned_identifiers_query = """
    #         DELETE FROM Identifier
    #         WHERE @rid NOT IN (
    #             SELECT DISTINCT `in`
    #             FROM HAS_IDENTIFIER
    #         )
    #         """
    #         await self.db.execute_command(
    #             delete_orphaned_identifiers_query, database_name
    #         )

    #         # Delete orphaned facts (not connected to any entity)
    #         delete_orphaned_facts_query = """
    #         DELETE FROM Fact
    #         WHERE @rid NOT IN (
    #             SELECT DISTINCT `in`
    #             FROM HAS_FACT
    #         )
    #         """
    #         await self.db.execute_command(delete_orphaned_facts_query, database_name)

    #         # Delete orphaned sources (not connected to any fact)
    #         delete_orphaned_sources_query = """
    #         DELETE FROM Source
    #         WHERE @rid NOT IN (
    #             SELECT DISTINCT `in`
    #             FROM DERIVED_FROM
    #         )
    #         """
    #         await self.db.execute_command(delete_orphaned_sources_query, database_name)

    #     except Exception as e:
    #         # Log the error but don't fail the cleanup
    #         print(f"Warning: Error during test data cleanup: {e}")
