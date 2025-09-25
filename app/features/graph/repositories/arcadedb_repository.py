"""Entity repository for database operations."""

from datetime import datetime
from typing import TypedDict, cast
from uuid import UUID

from app.db.arcadedb import GraphDB, get_database_name
from app.features.graph.models import (
    DerivedFrom,
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


# Internal types for Gremlin query results
class _FactData(TypedDict):
    fact_name: str
    fact_type: str
    fact_rel_verb: str
    fact_rel_confidence_score: float
    fact_rel_created_at: str
    source_id: str | None
    source_content: str | None
    source_timestamp: str | None


class _QueryResultRow(TypedDict):
    entity_id: str
    entity_created_at: str
    entity_metadata: dict[str, str]
    identifier_value: str
    identifier_type: str
    relationship_is_primary: bool
    relationship_created_at: str
    facts_with_sources: list[_FactData]


class _IdentifierWithRelData(TypedDict):
    value: str
    type: str
    is_primary: bool
    created_at: str


class _EntityByIdResultRow(TypedDict):
    entity_id: str
    entity_created_at: str
    entity_metadata: dict[str, str]
    identifiers_with_rel: list[_IdentifierWithRelData]
    facts_with_sources: list[_FactData]


class _GremlinResult(TypedDict):
    result: list[_EntityByIdResultRow]


class _SqlSelectResultRow(TypedDict):
    id: str
    created_at: str
    metadata: dict[str, str]


class _SqlResult(TypedDict):
    result: list[_SqlSelectResultRow]


class _SqlDeleteResult(TypedDict):
    result: list[dict[str, int]]


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


class IdentifierWithRelationship(TypedDict):
    """Groups the identifier used for the lookup with its relationship to the entity."""

    identifier: Identifier
    relationship: HasIdentifier


class FindEntityResult(TypedDict):
    """Result of finding an entity by its identifier, including facts and sources."""

    entity: Entity
    identifier: IdentifierWithRelationship
    facts_with_sources: list[FactWithSource]


class EntityWithRelations(TypedDict):
    """Complete entity data with all its relationships and associated objects."""

    entity: Entity
    identifiers: list[Identifier]
    facts_with_sources: list[FactWithSource]


class AddFactToEntityResult(TypedDict):
    """Result of adding a fact with source to an entity."""

    fact: Fact
    source: Source
    has_fact_relationship: HasFact
    derived_from_relationship: DerivedFrom


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

    async def find_entity_by_identifier(
        self, identifier_value: str, identifier_type: str
    ) -> FindEntityResult | None:
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

        # Gremlin query to fetch the entity, its identifier, and all its facts with their sources
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
            'relationship_created_at',
            'facts_with_sources'
        )
        .by(select('entity').values('id'))
        .by(select('entity').values('created_at'))
        .by(select('entity').values('metadata'))
        .by(select('identifier').values('value'))
        .by(select('identifier').values('type'))
        .by(select('rel').values('is_primary'))
        .by(select('rel').values('created_at'))
        .by(
            select('entity').outE('HAS_FACT').as('fact_rel')
            .inV().as('fact')
            .optional(outE('DERIVED_FROM').inV().as('source'))
            .project(
                'fact_name',
                'fact_type',
                'fact_rel_verb',
                'fact_rel_confidence_score',
                'fact_rel_created_at',
                'source_id',
                'source_content',
                'source_timestamp'
            )
            .by(select('fact').values('name'))
            .by(select('fact').values('type'))
            .by(select('fact_rel').values('verb'))
            .by(select('fact_rel').values('confidence_score'))
            .by(select('fact_rel').values('created_at'))
            .by(coalesce(select('source').values('id'), constant(null)))
            .by(coalesce(select('source').values('content'), constant(null)))
            .by(coalesce(select('source').values('timestamp'), constant(null)))
            .fold()
        )
        """

        try:
            # The result from a Gremlin query is a dictionary with a 'result' key
            # containing a list of dictionaries.
            GremlinResult = TypedDict(
                "GremlinResult", {"result": list[_QueryResultRow]}
            )
            query_response = cast(
                GremlinResult,
                await self.db.execute_command(
                    query,
                    database_name,
                    language="gremlin",
                ),
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
                id=UUID(row["entity_id"]),
                created_at=datetime.fromisoformat(row["entity_created_at"]),
                metadata=row["entity_metadata"] if row["entity_metadata"] else {},
            )

            # Parse the identifier data
            identifier = Identifier(
                value=row["identifier_value"],
                type=row["identifier_type"],
            )

            # Parse the relationship data
            has_identifier_rel = HasIdentifier(
                from_entity_id=entity.id,
                to_identifier_value=identifier.value,
                is_primary=row["relationship_is_primary"],
                created_at=datetime.fromisoformat(row["relationship_created_at"]),
            )

            # Parse facts and sources
            facts_with_sources: list[FactWithSource] = []
            if row["facts_with_sources"]:
                for fact_data in row["facts_with_sources"]:
                    fact = Fact(
                        name=fact_data["fact_name"],
                        type=fact_data["fact_type"],
                    )
                    if not fact.fact_id:
                        # This should not happen if the Fact model is correctly initialized
                        raise ValueError("Fact ID was not created for a new fact")

                    has_fact_rel = HasFact(
                        from_entity_id=entity.id,
                        to_fact_id=fact.fact_id,
                        verb=fact_data["fact_rel_verb"],
                        confidence_score=fact_data["fact_rel_confidence_score"],
                        created_at=datetime.fromisoformat(
                            fact_data["fact_rel_created_at"]
                        ),
                    )
                    source = None
                    if (
                        fact_data["source_id"]
                        and fact_data["source_content"]
                        and fact_data["source_timestamp"]
                    ):
                        source = Source(
                            id=UUID(fact_data["source_id"]),
                            content=fact_data["source_content"],
                            timestamp=datetime.fromisoformat(
                                fact_data["source_timestamp"]
                            ),
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

        except Exception as e:
            raise RuntimeError(f"Failed to find entity by identifier: {e}")

    async def find_entity_by_id(self, entity_id: str) -> FindEntityResult | None:
        """Find an entity by its ID and return it with all its relations.

        This method retrieves the entity along with:
        - All its identifiers and their relationships (via HAS_IDENTIFIER edges)
        - All its facts and their sources (via HAS_FACT and DERIVED_FROM edges)

        Args:
            entity_id: The UUID string of the entity to find

        Returns:
            FindEntityResult containing the entity, a primary or first identifier,
            and all facts with their sources, or None if the entity is not found.
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
            g.V().hasLabel('Entity').has('id', '{escaped_entity_id}').as('entity')
            .project(
                'entity_id',
                'entity_created_at',
                'entity_metadata',
                'identifiers_with_rel',
                'facts_with_sources'
            )
            .by(select('entity').values('id'))
            .by(select('entity').values('created_at'))
            .by(select('entity').values('metadata'))
            .by(
                select('entity').outE('HAS_IDENTIFIER').as('rel').inV().as('identifier')
                .project('value', 'type', 'is_primary', 'created_at')
                .by(select('identifier').values('value'))
                .by(select('identifier').values('type'))
                .by(select('rel').values('is_primary'))
                .by(select('rel').values('created_at'))
                .fold()
            )
            .by(
                select('entity').outE('HAS_FACT').as('fact_rel')
                .inV().as('fact')
                .optional(outE('DERIVED_FROM').inV().as('source'))
                .project(
                    'fact_name',
                    'fact_type',
                    'fact_rel_verb',
                    'fact_rel_confidence_score',
                    'fact_rel_created_at',
                    'source_id',
                    'source_content',
                    'source_timestamp'
                )
                .by(select('fact').values('name'))
                .by(select('fact').values('type'))
                .by(select('fact_rel').values('verb'))
                .by(select('fact_rel').values('confidence_score'))
                .by(select('fact_rel').values('created_at'))
                .by(coalesce(select('source').values('id'), constant(null)))
                .by(coalesce(select('source').values('content'), constant(null)))
                .by(coalesce(select('source').values('timestamp'), constant(null)))
                .fold()
            )
            """

            query_response = cast(
                _GremlinResult,
                await self.db.execute_command(
                    query,
                    database_name,
                    language="gremlin",
                ),
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
                id=UUID(row["entity_id"]),
                created_at=datetime.fromisoformat(row["entity_created_at"]),
                metadata=row["entity_metadata"] if row["entity_metadata"] else {},
            )

            # Parse identifiers and find the primary or first one
            identifiers_data = row["identifiers_with_rel"]
            if not identifiers_data:
                # This case should ideally not happen if entities are always created with an identifier
                raise RuntimeError(f"Entity with ID {entity_id} has no identifiers.")

            primary_identifier_data = next(
                (id_data for id_data in identifiers_data if id_data["is_primary"]),
                identifiers_data[0],
            )

            identifier = Identifier(
                value=primary_identifier_data["value"],
                type=primary_identifier_data["type"],
            )

            has_identifier_rel = HasIdentifier(
                from_entity_id=entity.id,
                to_identifier_value=identifier.value,
                is_primary=primary_identifier_data["is_primary"],
                created_at=datetime.fromisoformat(
                    primary_identifier_data["created_at"]
                ),
            )

            # Parse facts and sources
            facts_with_sources: list[FactWithSource] = []
            if row["facts_with_sources"]:
                for fact_data in row["facts_with_sources"]:
                    fact = Fact(
                        name=fact_data["fact_name"],
                        type=fact_data["fact_type"],
                    )
                    if not fact.fact_id:
                        # This should not happen if the Fact model is correctly initialized
                        raise ValueError("Fact ID was not created for a new fact")

                    has_fact_rel = HasFact(
                        from_entity_id=entity.id,
                        to_fact_id=fact.fact_id,
                        verb=fact_data["fact_rel_verb"],
                        confidence_score=fact_data["fact_rel_confidence_score"],
                        created_at=datetime.fromisoformat(
                            fact_data["fact_rel_created_at"]
                        ),
                    )
                    source = None
                    if (
                        fact_data["source_id"]
                        and fact_data["source_content"]
                        and fact_data["source_timestamp"]
                    ):
                        source = Source(
                            id=UUID(fact_data["source_id"]),
                            content=fact_data["source_content"],
                            timestamp=datetime.fromisoformat(
                                fact_data["source_timestamp"]
                            ),
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
            check_result = cast(
                _SqlResult,
                await self.db.execute_command(
                    check_query, database_name, language="sql"
                ),
            )

            if not check_result or not check_result.get("result"):
                return False

            # Delete the entity (edges are automatically removed)
            delete_query = f"DELETE VERTEX FROM Entity WHERE id = '{entity_id}'"
            delete_result = cast(
                _SqlDeleteResult,
                await self.db.execute_command(
                    delete_query, database_name, language="sql"
                ),
            )

            return bool(
                delete_result
                and delete_result.get("result")
                and delete_result["result"][0].get("count", 0) > 0
            )

        except Exception as e:
            raise RuntimeError(f"Failed to delete entity: {e}")

    async def add_fact_to_entity(
        self,
        entity_id: str,
        fact: Fact,
        source: Source,
        verb: str,
        confidence_score: float = 1.0,
    ) -> AddFactToEntityResult:
        """Add a fact with its source to an existing entity.

        This method creates a fact vertex, a source vertex, and establishes
        the relationships between them and the entity in a single transaction.

        Args:
            entity_id: The UUID string of the entity to add the fact to
            fact: The Fact object to create
            source: The Source object providing the origin of the fact
            verb: The semantic relationship verb (e.g., 'lives_in', 'works_at')
            confidence_score: Confidence level of this fact (0.0 to 1.0)

        Returns:
            AddFactToEntityResult containing the created fact, source, and relationships

        Raises:
            ValueError: If entity_id is empty or fact/source are invalid
            RuntimeError: If the operation fails
        """
        if not entity_id:
            raise ValueError("Entity ID cannot be empty")
        if not fact.fact_id:
            raise ValueError("Fact must have a valid fact_id")
        if not verb or not verb.strip():
            raise ValueError("Verb cannot be empty")

        database_name = get_database_name()

        # Validate confidence score
        if not (0.0 <= confidence_score <= 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")

        try:
            # Create fact, source, and relationships in a single transaction
            transaction_script = """
            BEGIN;
            -- Create or update fact vertex
            UPDATE Fact
            SET name = :fact_name, type = :fact_type
            UPSERT WHERE fact_id = :fact_id;
            -- Create source vertex
            CREATE VERTEX Source
            SET id = :source_id,
                content = :source_content,
                timestamp = :source_timestamp;
            -- Create HAS_FACT relationship from entity to fact
            CREATE EDGE HAS_FACT
            FROM (SELECT FROM Entity WHERE id = :entity_id)
            TO (SELECT FROM Fact WHERE fact_id = :fact_id)
            SET verb = :verb,
                confidence_score = :confidence_score,
                created_at = :created_at;
            -- Create DERIVED_FROM relationship from fact to source
            CREATE EDGE DERIVED_FROM
            FROM (SELECT FROM Fact WHERE fact_id = :fact_id)
            TO (SELECT FROM Source WHERE id = :source_id)
            SET created_at = :created_at;
            COMMIT;
            """

            params = {
                "entity_id": entity_id,
                "fact_id": fact.fact_id,
                "fact_name": fact.name,
                "fact_type": fact.type,
                "source_id": str(source.id),
                "source_content": source.content,
                "source_timestamp": source.timestamp.isoformat(),
                "verb": verb.strip().lower(),
                "confidence_score": confidence_score,
                "created_at": datetime.now().isoformat(),
            }

            created_result = cast(
                _TransactionResult,
                await self.db.execute_command(
                    transaction_script,
                    database_name,
                    parameters=params,
                    language="sqlscript",
                ),
            )

            # Check if transaction was successful
            if "result" not in created_result or not created_result["result"]:
                raise RuntimeError("Failed to add fact to entity")

            # Create the relationship objects to return
            has_fact_relationship = HasFact(
                from_entity_id=UUID(entity_id),
                to_fact_id=fact.fact_id,
                verb=verb.strip().lower(),
                confidence_score=confidence_score,
                created_at=datetime.now(),
            )

            derived_from_relationship = DerivedFrom(
                from_fact_id=fact.fact_id,
                to_source_id=source.id,
            )

            return {
                "fact": fact,
                "source": source,
                "has_fact_relationship": has_fact_relationship,
                "derived_from_relationship": derived_from_relationship,
            }

        except Exception as e:
            raise RuntimeError(f"Failed to add fact to entity: {e}")
