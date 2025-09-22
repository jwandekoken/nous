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


class ArcadedbRepository:
    """Handles all graph database operations."""

    def __init__(self, db: GraphDB):
        self.db: GraphDB = db

    # @TODO: verify if this method is idempotent (add test for this)
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
            UPDATE Identifier
            SET value = :identifier_value, type = :identifier_type
            UPSERT WHERE value = :identifier_value AND type = :identifier_type;
            CREATE EDGE HAS_IDENTIFIER
            FROM (SELECT FROM Entity WHERE id = :entity_id)
            TO (SELECT FROM Identifier WHERE value = :identifier_value AND type = :identifier_type)
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

        try:
            # Use Gremlin to find entity by ID and optionally get its identifiers
            # Note: ArcadeDB doesn't support parameterized Gremlin queries, so we use string formatting
            # with proper escaping for security
            escaped_entity_id = entity_id.replace("'", "\\'")

            query = f"""
            g.V().hasLabel('Entity').has('id', '{escaped_entity_id}')
            .project(
                'entity_id',
                'entity_created_at',
                'entity_metadata',
                'identifiers'
            )
            .by(values('id'))
            .by(values('created_at'))
            .by(values('metadata'))
            .by(
                outE('HAS_IDENTIFIER').inV()
                .project('value', 'type')
                .by(values('value'))
                .by(values('type'))
                .fold()
            )
            """

            query_response = await self.db.execute_command(
                query,
                database_name,
                language="gremlin",
            )

            if (
                not query_response
                or "result" not in query_response
                or not query_response["result"]
            ):
                return None

            # Parse the result
            row = query_response["result"][0]

            # Parse entity data
            entity = Entity(
                id=row["entity_id"],
                created_at=row["entity_created_at"],
                metadata=row["entity_metadata"] if row["entity_metadata"] else {},
            )

            # Parse identifiers data
            identifiers = []
            if row["identifiers"]:
                for identifier_data in row["identifiers"]:
                    identifier = Identifier(
                        value=identifier_data["value"],
                        type=identifier_data["type"],
                    )
                    identifiers.append(identifier)

            return {
                "entity": entity,
                "identifiers": identifiers,
                "facts_with_sources": [],
            }

        except Exception as e:
            raise RuntimeError(f"Failed to find entity by id: {e}")

    async def delete_entity_by_id(self, entity_id: str) -> bool:
        """Delete an entity by its ID.

        This method deletes the entity vertex. Connected edges are automatically
        removed by ArcadeDB, but connected vertices (identifiers, facts, sources)
        are not deleted to avoid breaking other entities that might reference them.

        Returns True if the entity was found and deleted, False if not found.
        """
        if not entity_id:
            raise ValueError("Entity ID cannot be empty")

        database_name = get_database_name()

        try:
            # Check if entity exists
            check_query = f"SELECT FROM Entity WHERE id = '{entity_id}'"
            check_result = await self.db.execute_command(
                check_query, database_name, language="sql"
            )

            if not check_result or not check_result.get("result"):
                return False

            # Delete the entity (edges are automatically removed)
            delete_query = f"DELETE VERTEX FROM Entity WHERE id = '{entity_id}'"
            delete_result = await self.db.execute_command(
                delete_query, database_name, language="sql"
            )

            return bool(
                delete_result
                and delete_result.get("result")
                and delete_result["result"][0].get("count", 0) > 0
            )

        except Exception as e:
            raise RuntimeError(f"Failed to delete entity: {e}")
