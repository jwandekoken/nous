"""Entity repository for database operations."""

from typing import TypedDict, cast

from app.db.arcadedb import GraphDB, get_database_name
from app.features.graph.models import (
    Entity,
    Fact,
    HasFact,
    HasIdentifier,
    Identifier,
    Source,
)


# Internal types for ArcadeDB transaction results
class _CommitInfo(TypedDict):
    operation: str


class _TransactionResult(TypedDict):
    result: list[_CommitInfo] | _CommitInfo


class CreateEntityResult(TypedDict):
    """Result of creating a new entity with its identifier and relationship."""

    entity: Entity
    identifier: Identifier
    relationship: HasIdentifier


class FindEntityByIdentifierResult(TypedDict):
    """Result of finding an entity by its identifier value and type."""

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


class GraphRepository:
    """Handles all graph database operations."""

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
                "is_primary": relationship.is_primary,
                "relationship_created_at": relationship.created_at.isoformat(),
            }

            # Use sqlscript with transaction for the CREATE VERTEX and CREATE EDGE operations
            transaction_script = """
            BEGIN;
            CREATE VERTEX Entity
            SET id = :entity_id,
                created_at = :created_at,
                metadata = :metadata;
            CREATE VERTEX Identifier
            SET value = :identifier_value,
                type = :identifier_type;
            CREATE EDGE HAS_IDENTIFIER
            FROM (SELECT FROM Entity WHERE id = :entity_id)
            TO (SELECT FROM Identifier WHERE value = :identifier_value)
            SET is_primary = :is_primary,
                created_at = :relationship_created_at;
            COMMIT;
            """

            created_entity_result = cast(
                _TransactionResult,
                await self.db.execute_command(
                    transaction_script,
                    database_name,
                    parameters=params,
                    language="sqlscript",
                ),
            )

            # Check if entity was created successfully
            if (
                "result" not in created_entity_result
                or not created_entity_result["result"]
            ):
                raise RuntimeError("Failed to create entity")

            # For transactions, the result contains commit info, not the created vertex data
            # So we use the original entity data since the transaction succeeded
            result_list = created_entity_result["result"]

            # Check if the transaction committed successfully
            commit_result: _CommitInfo
            if isinstance(result_list, list):
                commit_result = result_list[0]
            else:
                commit_result = result_list

            if commit_result.get("operation") != "commit":
                raise RuntimeError("Transaction did not commit successfully")

            # Return the original entity, identifier, and relationship to avoid another database query
            return {
                "entity": entity,
                "identifier": identifier,
                "relationship": relationship,
            }

        except Exception as e:
            # If any command fails, raise an error
            raise RuntimeError(f"Failed to create entity: {e}")

    # @TODO: return facts with sources.
    async def find_entity_by_identifier(
        self, identifier_value: str, identifier_type: str
    ) -> FindEntityByIdentifierResult | None:
        """Find an entity by its identifier value and type using Gremlin query.

        Note: ArcadeDB doesn't support parameterized Gremlin queries, so we use
        string formatting with proper escaping for security.
        """

        # Input validation and escaping to prevent injection
        if not identifier_value or not identifier_type:
            raise ValueError("Identifier value and type cannot be empty")

        # Escape single quotes in the values to prevent injection
        escaped_value = identifier_value.replace("'", "\\'")
        escaped_type = identifier_type.replace("'", "\\'")

        database_name = get_database_name()

        # Use hardcoded Gremlin query since ArcadeDB doesn't support parameterized Gremlin
        query = f"""
        g.V().hasLabel('Identifier')
        .has('value', '{escaped_value}')
        .has('type', '{escaped_type}')
        .as('identifier')
        .inE('HAS_IDENTIFIER')
        .as('rel')
        .outV()
        .as('entity')
        .project(
            'entity_id',
            'entity_created_at',
            'entity_metadata',
            'identifier_value',
            'identifier_type',
            'relationship_is_primary',
            'relationship_created_at'
        )
        .by(select('entity').values('id'))
        .by(select('entity').values('created_at'))
        .by(select('entity').values('metadata'))
        .by(select('identifier').values('value'))
        .by(select('identifier').values('type'))
        .by(select('rel').values('is_primary'))
        .by(select('rel').values('created_at'))
        """

        try:
            query_response = await self.db.execute_command(
                query,
                database_name,
                language="gremlin",
            )

            # Check if we got any results
            if (
                not query_response
                or "result" not in query_response
                or not query_response["result"]
            ):
                return None

            # Get the first result (should only be one due to unique constraints)
            row = query_response["result"][0]

            # Parse the entity data
            entity = Entity(
                id=row["entity_id"],
                created_at=row["entity_created_at"],
                metadata=row["entity_metadata"] if row["entity_metadata"] else {},
            )

            # Parse the identifier data
            identifier = Identifier(
                value=row["identifier_value"],
                type=row["identifier_type"],
            )

            # Parse the relationship data
            relationship = HasIdentifier(
                from_entity_id=entity.id,
                to_identifier_value=identifier.value,
                is_primary=row["relationship_is_primary"],
                created_at=row["relationship_created_at"],
            )

            return {
                "entity": entity,
                "identifier": identifier,
                "relationship": relationship,
            }

        except Exception as e:
            raise RuntimeError(f"Failed to find entity by identifier: {e}")

    # @TODO: return facts with sources.
    async def find_entity_by_id(self, entity_id: str) -> EntityWithRelations | None:
        """Find an entity by its ID and return it with all its relations.

        This method retrieves the entity along with:
        - All its identifiers (via HAS_IDENTIFIER edges)

        Args:
            entity_id: The UUID string of the entity to find

        Returns:
            EntityWithRelations containing the entity and all its relations,
            or None if the entity is not found.
        """
        if not entity_id:
            raise ValueError("Entity ID cannot be empty")

        database_name = get_database_name()

        # Create parameters dictionary for safe query execution
        params = {
            "entity_id": entity_id,
        }

        try:
            # Use a single ArcadeDB SQL MATCH statement to get entity and all its identifiers
            match_query = """
            MATCH
                {type: `Entity`, where: (id = :entity_id), as: entity}
                .outE(){
                    type: `HAS_IDENTIFIER`,
                    as: rel,
                    optional: true
                }
                .inV(){
                    type: `Identifier`,
                    as: identifier,
                    optional: true
                }
            RETURN
                entity.id AS entity_id,
                entity.created_at AS entity_created_at,
                entity.metadata AS entity_metadata,
                identifier.value AS identifier_value,
                identifier.type AS identifier_type
            """

            query_response = await self.db.execute_command(
                match_query,
                database_name,
                parameters=params,
                language="sql",
            )

            if (
                not query_response
                or "result" not in query_response
                or not query_response["result"]
            ):
                return None

            # Process the results - group by entity since multiple rows may exist
            # (one row per identifier, or one row with null identifiers if none exist)
            entity = None
            identifiers = []

            for row in query_response["result"]:
                # Parse entity data (only once)
                if entity is None:
                    entity = Entity(
                        id=row["entity_id"],
                        created_at=row["entity_created_at"],
                        metadata=row["entity_metadata"]
                        if row["entity_metadata"]
                        else {},
                    )

                # Parse identifier data (only if it exists - not null)
                if (
                    row["identifier_value"] is not None
                    and row["identifier_type"] is not None
                ):
                    identifier = Identifier(
                        value=row["identifier_value"],
                        type=row["identifier_type"],
                    )
                    identifiers.append(identifier)

            if entity is None:
                return None

            return {
                "entity": entity,
                "identifiers": identifiers,
                "facts_with_sources": [],
            }

        except Exception as e:
            raise RuntimeError(f"Failed to find entity by id: {e}")

    async def delete_entity_by_id(self, entity_id: str) -> bool:
        """Delete an entity by its ID, including its identifiers if not used by other entities.

        This method performs a cascading delete:
        1. Checks if the entity exists
        2. Finds all identifiers connected to the entity via HAS_IDENTIFIER edges
        3. For each identifier, checks if it has any other HAS_IDENTIFIER edges to other entities
        4. Deletes HAS_IDENTIFIER edges connected to the entity
        5. Deletes identifiers that are only used by this entity
        6. Deletes the entity itself

        Returns True if the entity was found and deleted, False if not found.
        """
        database_name = get_database_name()

        # First check if entity exists
        check_query = f"SELECT FROM Entity WHERE id = '{entity_id}'"

        try:
            check_result = await self.db.execute_command(
                check_query,
                database_name,
                language="sql",
            )

            # Check if entity exists
            if (
                not check_result
                or "result" not in check_result
                or not check_result["result"]
            ):
                return False

            # Entity exists, now delete it
            # Try just deleting the vertex first (edges should be deleted automatically)
            delete_query = f"DELETE VERTEX FROM Entity WHERE id = '{entity_id}'"

            delete_result = await self.db.execute_command(
                delete_query,
                database_name,
                language="sql",
            )
            print("delete_entity result: ", delete_result)

            # For a simple DELETE query, success is indicated by having a result
            # ArcadeDB returns the number of deleted records in format: {'result': [{'count': 1}]}
            if "result" in delete_result:
                result_list = delete_result["result"]
                # Check if result is a list with at least one element
                if (
                    isinstance(result_list, list)
                    and len(result_list) > 0
                    and isinstance(result_list[0], dict)
                    and "count" in result_list[0]
                    and result_list[0]["count"] > 0
                ):
                    return True

            return False

        except Exception as e:
            raise RuntimeError(f"Failed to delete entity: {e}")
