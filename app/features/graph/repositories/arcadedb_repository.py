"""Entity repository for database operations."""

from datetime import datetime
from typing import TypedDict, cast
from uuid import UUID

from app.db.arcadedb import ArcadeDB, get_database_name
from app.features.graph.models import (
    DerivedFrom,
    Entity,
    Fact,
    HasFact,
    HasIdentifier,
    Identifier,
    Source,
)

from .types import (
    AddFactToEntityResult,
    CreateEntityResult,
    FactWithOptionalSource,
    FindEntityByIdResult,
    FindEntityResult,
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


class _FindEntityByIdentifierResultRow(TypedDict):
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


class _FindEntityByIdResultRow(TypedDict):
    entity_id: str
    entity_created_at: str
    entity_metadata: dict[str, str]
    identifiers_with_rel: list[_IdentifierWithRelData]
    facts_with_sources: list[_FactData]


class _FindEntityByIdGremlinResult(TypedDict):
    result: list[_FindEntityByIdResultRow]


class _FindFactByIdResultRow(TypedDict):
    fact_name: str
    fact_type: str
    fact_id: str
    source_id: str | None
    source_content: str | None
    source_timestamp: str | None


class _FindFactByIdGremlinResult(TypedDict):
    result: list[_FindFactByIdResultRow]


class _GetExistingFactRelationshipsResultRow(TypedDict):
    fact_name: str
    fact_type: str
    fact_id: str
    source_id: str
    source_content: str
    source_timestamp: str
    verb: str
    confidence_score: float
    has_fact_created_at: str
    derived_created_at: str


class _GetExistingFactRelationshipsGremlinResult(TypedDict):
    result: list[_GetExistingFactRelationshipsResultRow]


class _HasFactEdgeCountGremlinResult(TypedDict):
    result: list[dict[str, int] | int]


class _EntityExistsCheckSqlResultRow(TypedDict):
    id: str
    created_at: str
    metadata: dict[str, str]


class _EntityExistsCheckSqlResult(TypedDict):
    result: list[_EntityExistsCheckSqlResultRow]


class _SqlDeleteResult(TypedDict):
    result: list[dict[str, int]]


class ArcadedbRepository:
    """Handles all graph database operations."""

    def __init__(self, db: ArcadeDB):
        self.db: ArcadeDB = db

    async def create_entity(
        self, entity: Entity, identifier: Identifier, relationship: HasIdentifier
    ) -> CreateEntityResult:
        """Create a new entity with identifier in the database using ArcadeDB SQL.

        This method is idempotent: if an entity with the given identifier already exists,
        it returns the existing entity instead of creating a duplicate.

        Args:
            entity: The Entity object to create
            identifier: The Identifier to associate with the entity
            relationship: The HasIdentifier relationship between entity and identifier

        Returns:
            CreateEntityResult containing the entity (existing or newly created),
            identifier, and relationship
        """

        # Check if entity with this identifier already exists
        existing_entity = await self.find_entity_by_identifier(
            identifier.value, identifier.type
        )

        if existing_entity is not None:
            # Entity already exists, return it
            return {
                "entity": existing_entity["entity"],
                "identifier": existing_entity["identifier"]["identifier"],
                "relationship": existing_entity["identifier"]["relationship"],
            }

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
                "GremlinResult", {"result": list[_FindEntityByIdentifierResultRow]}
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

    async def find_entity_by_id(self, entity_id: str) -> FindEntityByIdResult | None:
        """Find an entity by its ID and return it with all its relations.

        This method retrieves the entity along with:
        - All its identifiers and their relationships (via HAS_IDENTIFIER edges)
        - All its facts and their sources (via HAS_FACT and DERIVED_FROM edges)

        Args:
            entity_id: The UUID string of the entity to find

        Returns:
            FindEntityByIdResult containing the entity, its primary identifier (or None if no identifiers),
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
                _FindEntityByIdGremlinResult,
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

            # Parse identifiers - find primary or first one, or None if no identifiers
            identifiers_data = row["identifiers_with_rel"]
            identifier_with_relationship: IdentifierWithRelationship | None = None
            if identifiers_data:
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

                identifier_with_relationship = {
                    "identifier": identifier,
                    "relationship": has_identifier_rel,
                }

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

            result: FindEntityByIdResult = {
                "entity": entity,
                "identifier": identifier_with_relationship,
                "facts_with_sources": facts_with_sources,
            }
            return result

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
                _EntityExistsCheckSqlResult,
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
        create_source: bool = True,
    ) -> AddFactToEntityResult:
        """Add a fact with its source to an existing entity.

        This method is fully idempotent: if the same fact is added multiple times
        to the same entity, it returns the existing relationships without creating duplicates.

        Args:
            entity_id: The UUID string of the entity to add the fact to
            fact: The Fact object to create
            source: The Source object providing the origin of the fact
            verb: The semantic relationship verb (e.g., 'lives_in', 'works_at')
            confidence_score: Confidence level of this fact (0.0 to 1.0)
            create_source: If True, creates the source vertex. If False, assumes source already exists.

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

        # Check if HAS_FACT edge already exists (for idempotency)
        if await self._check_has_fact_edge_exists(entity_id, fact.fact_id):
            # Edge exists - return existing relationships
            return await self._get_existing_fact_relationships(entity_id, fact.fact_id)

        try:
            # Create fact, source, and relationships in a single transaction
            # This code only runs if the HAS_FACT edge doesn't already exist

            # Format timestamps for ArcadeDB (ArcadeDB doesn't handle parameterized DATETIME well)
            # Use format: 'YYYY-MM-DD HH:MM:SS'
            source_timestamp_str = source.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            created_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if create_source:
                source_creation = f"""
                UPDATE Source
                SET id = :source_id,
                    content = :source_content,
                    timestamp = '{source_timestamp_str}'
                UPSERT WHERE id = :source_id;
                """
            else:
                source_creation = ""

            transaction_script = f"""
            BEGIN;
            UPDATE Fact
            SET name = :fact_name, type = :fact_type
            UPSERT WHERE fact_id = :fact_id;
            {source_creation}
            CREATE EDGE HAS_FACT
            FROM (SELECT FROM Entity WHERE id = :entity_id)
            TO (SELECT FROM Fact WHERE fact_id = :fact_id)
            SET verb = :verb,
                confidence_score = :confidence_score,
                created_at = '{created_at_str}';
            CREATE EDGE DERIVED_FROM
            FROM (SELECT FROM Fact WHERE fact_id = :fact_id)
            TO (SELECT FROM Source WHERE id = :source_id)
            SET created_at = '{created_at_str}';
            COMMIT;
            """

            params = {
                "entity_id": entity_id,
                "fact_id": fact.fact_id,
                "fact_name": fact.name,
                "fact_type": fact.type,
                "source_id": str(source.id),
                "source_content": source.content,
                "verb": verb.strip().lower(),
                "confidence_score": confidence_score,
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

    async def find_fact_by_id(self, fact_id: str) -> FactWithOptionalSource | None:
        """Find a fact by its fact_id.

        Args:
            fact_id: The synthetic fact_id (e.g., 'Location:Paris')

        Returns:
            FactWithOptionalSource containing the fact and its linked source if found, None if not found.
        """
        if not fact_id or not fact_id.strip():
            raise ValueError("Fact ID cannot be empty")

        database_name = get_database_name()

        try:
            # Use Gremlin to find fact by fact_id
            escaped_fact_id = fact_id.replace("'", "\\'")

            query = f"""
            g.V().hasLabel('Fact').has('fact_id', '{escaped_fact_id}').as('fact')
            .project(
                'fact_name',
                'fact_type',
                'fact_id',
                'source_id',
                'source_content',
                'source_timestamp'
            )
            .by(select('fact').values('name'))
            .by(select('fact').values('type'))
            .by(select('fact').values('fact_id'))
            .by(coalesce(select('fact').outE('DERIVED_FROM').inV().values('id'), constant(null)))
            .by(coalesce(select('fact').outE('DERIVED_FROM').inV().values('content'), constant(null)))
            .by(coalesce(select('fact').outE('DERIVED_FROM').inV().values('timestamp'), constant(null)))
            """

            query_response = cast(
                _FindFactByIdGremlinResult,
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

            # Parse fact data
            fact = Fact(
                name=row["fact_name"],
                type=row["fact_type"],
            )
            # The fact_id should be automatically set by the model validator

            # Parse source data
            source = None
            if row["source_id"] and row["source_content"] and row["source_timestamp"]:
                source = Source(
                    id=UUID(row["source_id"]),
                    content=row["source_content"],
                    timestamp=datetime.fromisoformat(row["source_timestamp"]),
                )

            return {
                "fact": fact,
                "source": source,
            }

        except Exception as e:
            raise RuntimeError(f"Failed to find fact by id: {e}")

    async def _check_has_fact_edge_exists(self, entity_id: str, fact_id: str) -> bool:
        """Check if HAS_FACT edge exists between entity and fact.

        Args:
            entity_id: The UUID string of the entity
            fact_id: The fact_id of the fact

        Returns:
            True if the HAS_FACT edge exists, False otherwise
        """
        database_name = get_database_name()

        try:
            # Use Gremlin to check if edge exists - more reliable than SQL for edges
            escaped_entity_id = entity_id.replace("'", "\\'")
            escaped_fact_id = fact_id.replace("'", "\\'")

            check_query = f"""
            g.V().hasLabel('Entity').has('id', '{escaped_entity_id}')
              .outE('HAS_FACT')
              .where(inV().has('fact_id', '{escaped_fact_id}'))
              .count()
            """

            result = cast(
                _HasFactEdgeCountGremlinResult,
                await self.db.execute_command(
                    check_query,
                    database_name,
                    language="gremlin",
                ),
            )

            # Gremlin count returns nested result structure
            result_list = result.get("result", [])
            if result_list and isinstance(result_list[0], dict):
                count = result_list[0].get("result", 0)
            else:
                count = result_list[0] if result_list else 0

            return cast(int, count) > 0

        except Exception as e:
            raise RuntimeError(f"Failed to check if HAS_FACT edge exists: {e}")

    async def _get_existing_fact_relationships(
        self, entity_id: str, fact_id: str
    ) -> AddFactToEntityResult:
        """Retrieve existing fact and its relationships.

        Args:
            entity_id: The UUID string of the entity
            fact_id: The fact_id of the fact
            source_id: The UUID string of the source

        Returns:
            AddFactToEntityResult containing the existing fact, source, and relationships
        """
        database_name = get_database_name()

        try:
            # Use Gremlin to get the fact, source, and relationships
            escaped_entity_id = entity_id.replace("'", "\\'")
            escaped_fact_id = fact_id.replace("'", "\\'")

            query = f"""
            g.V().hasLabel('Entity').has('id', '{escaped_entity_id}')
              .outE('HAS_FACT')
              .where(inV().has('fact_id', '{escaped_fact_id}'))
              .as('has_fact_edge')
              .inV().as('fact')
              .outE('DERIVED_FROM').as('derived_edge')
              .inV().as('source')
              .project(
                  'fact_name', 'fact_type', 'fact_id',
                  'source_id', 'source_content', 'source_timestamp',
                  'verb', 'confidence_score', 'has_fact_created_at',
                  'derived_created_at'
              )
              .by(select('fact').values('name'))
              .by(select('fact').values('type'))
              .by(select('fact').values('fact_id'))
              .by(select('source').values('id'))
              .by(select('source').values('content'))
              .by(select('source').values('timestamp'))
              .by(select('has_fact_edge').values('verb'))
              .by(select('has_fact_edge').values('confidence_score'))
              .by(select('has_fact_edge').values('created_at'))
              .by(select('derived_edge').values('created_at'))
            """

            query_response = cast(
                _GetExistingFactRelationshipsGremlinResult,
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
                raise RuntimeError("Failed to retrieve existing fact relationships")

            # Parse the result
            row = query_response["result"][0]

            # Parse fact data
            fact = Fact(
                name=row["fact_name"],
                type=row["fact_type"],
            )

            # Parse source data
            source = Source(
                id=UUID(row["source_id"]),
                content=row["source_content"],
                timestamp=datetime.fromisoformat(row["source_timestamp"]),
            )

            # Parse relationships
            has_fact_relationship = HasFact(
                from_entity_id=UUID(entity_id),
                to_fact_id=row["fact_id"],
                verb=row["verb"],
                confidence_score=row["confidence_score"],
                created_at=datetime.fromisoformat(row["has_fact_created_at"]),
            )

            derived_from_relationship = DerivedFrom(
                from_fact_id=row["fact_id"],
                to_source_id=source.id,
            )

            return {
                "fact": fact,
                "source": source,
                "has_fact_relationship": has_fact_relationship,
                "derived_from_relationship": derived_from_relationship,
            }

        except Exception as e:
            raise RuntimeError(f"Failed to get existing fact relationships: {e}")
