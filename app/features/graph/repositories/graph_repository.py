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
            print("created_entity_result: ", created_entity_result)

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

    async def find_entity_by_identifier(
        self, identifier_value: str, identifier_type: str
    ) -> FindEntityByIdentifierResult | None:
        """Find an entity by its identifier value and type using ArcadeDB SQL."""

        database_name = get_database_name()

        # Query to find entity by identifier value and type
        # @TODO: Fix this query - relationship is not being returned
        query = """
        MATCH
            {type: `Identifier`, where: (value = :identifier_value AND type = :identifier_type), as: identifier}
            <-HAS_IDENTIFIER-
            {type: `Entity`, as: entity}
        RETURN
            entity.id AS entity_id,
            entity.created_at AS entity_created_at,
            entity.metadata AS entity_metadata,
            identifier.value AS identifier_value,
            identifier.type AS identifier_type,
            rel.is_primary AS relationship_is_primary,
            rel.created_at AS relationship_created_at
        """

        try:
            result = await self.db.execute_command(
                query,
                database_name,
                parameters={
                    "identifier_value": identifier_value,
                    "identifier_type": identifier_type,
                },
                language="sql",
            )

            print("result: ", result)

            # Check if we got any results
            if not result or "result" not in result or not result["result"]:
                return None

            # Get the first result (should only be one due to unique constraints)
            row = result["result"][0]

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
