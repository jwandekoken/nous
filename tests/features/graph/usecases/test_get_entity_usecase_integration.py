"""Integration tests for GetEntityUseCaseImpl using real dependencies.

This module provides integration tests for the GetEntityUseCaseImpl
using the actual production implementation of ArcadedbRepository.
"""

import uuid
from datetime import datetime

import pytest

from app.db.arcadedb import GraphDB, get_database_name, get_graph_db, reset_graph_db
from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    GetEntityResponse,
    IdentifierDto,
)
from app.features.graph.repositories.arcadedb_repository import ArcadedbRepository
from app.features.graph.services.langchain_fact_extractor import LangChainFactExtractor
from app.features.graph.usecases.assimilate_knowledge_usecase import (
    AssimilateKnowledgeUseCaseImpl,
)
from app.features.graph.usecases.get_entity_usecase import GetEntityUseCaseImpl


@pytest.fixture(autouse=True)
async def reset_db_connection():
    """Reset database connection and clear data before each test."""
    await reset_graph_db()

    # Clear all data from the database to ensure clean state
    db = await get_graph_db()
    database_name = get_database_name()

    # Delete all vertices and edges in reverse dependency order
    clear_commands = [
        "DELETE FROM DERIVED_FROM",
        "DELETE FROM HAS_FACT",
        "DELETE FROM HAS_IDENTIFIER",
        "DELETE FROM Fact",
        "DELETE FROM Source",
        "DELETE FROM Identifier",
        "DELETE FROM Entity",
    ]

    for command in clear_commands:
        try:
            await db.execute_command(command, database_name, language="sql")
        except Exception:
            pass  # Ignore errors if tables don't exist or are already empty


@pytest.fixture
async def graph_db() -> GraphDB:
    """Real database connection for integration tests."""
    return await get_graph_db()


@pytest.fixture
async def arcadedb_repository(graph_db: GraphDB) -> ArcadedbRepository:
    """ArcadedbRepository instance for testing."""
    return ArcadedbRepository(graph_db)


@pytest.fixture
def langchain_fact_extractor() -> LangChainFactExtractor:
    """LangChainFactExtractor instance for testing."""
    return LangChainFactExtractor()


@pytest.fixture
async def assimilate_knowledge_usecase(
    arcadedb_repository: ArcadedbRepository,
    langchain_fact_extractor: LangChainFactExtractor,
) -> AssimilateKnowledgeUseCaseImpl:
    """AssimilateKnowledgeUseCaseImpl instance for setting up test data."""
    return AssimilateKnowledgeUseCaseImpl(
        repository=arcadedb_repository, fact_extractor=langchain_fact_extractor
    )


@pytest.fixture
async def get_entity_usecase(
    arcadedb_repository: ArcadedbRepository,
) -> GetEntityUseCaseImpl:
    """GetEntityUseCaseImpl instance for testing."""
    return GetEntityUseCaseImpl(repository=arcadedb_repository)


@pytest.fixture
def test_identifier() -> IdentifierDto:
    """Test identifier payload for integration testing."""
    return IdentifierDto(
        value=f"test.integration.{uuid.uuid4()}@example.com", type="email"
    )


@pytest.fixture
def test_content() -> str:
    """Test content for fact extraction."""
    return "I live in Paris and work as a Software Engineer. I really enjoy hiking on weekends."


class TestGetEntityUseCaseIntegration:
    """Integration tests for GetEntityUseCaseImpl.execute method."""

    @pytest.mark.asyncio
    async def test_get_entity_existing_entity(
        self,
        get_entity_usecase: GetEntityUseCaseImpl,
        assimilate_knowledge_usecase: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
        test_content: str,
    ) -> None:
        """Test retrieving an existing entity by identifier."""

        # First, create an entity with facts using assimilate knowledge
        assimilate_request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content=test_content,
        )
        _ = await assimilate_knowledge_usecase.execute(assimilate_request)

        # Now retrieve the entity using get entity use case
        result: GetEntityResponse = await get_entity_usecase.execute(
            identifier_value=test_identifier.value, identifier_type=test_identifier.type
        )
        print(f"{result=}")

        # Assert
        assert isinstance(result, GetEntityResponse)
        assert result.entity is not None
        assert result.identifier is not None
        assert result.facts is not None

        # Verify entity details
        assert result.entity.id is not None
        assert isinstance(result.entity.metadata, dict)

        # Verify identifier details
        assert result.identifier.identifier.value == test_identifier.value
        assert result.identifier.identifier.type == test_identifier.type
        assert result.identifier.relationship.is_primary is True
        assert result.identifier.relationship.created_at is not None

        # Verify facts were included (should have facts from assimilation)
        assert len(result.facts) > 0

        # Check structure of facts with sources
        for fact_with_source in result.facts:
            assert fact_with_source.fact is not None
            assert fact_with_source.fact.name is not None
            assert fact_with_source.fact.type is not None
            assert fact_with_source.fact.fact_id is not None
            assert fact_with_source.relationship is not None
            assert fact_with_source.relationship.verb is not None
            assert 0.0 <= fact_with_source.relationship.confidence_score <= 1.0
            assert fact_with_source.relationship.created_at is not None
            # Source should always be present for facts created through assimilation
            assert fact_with_source.source is not None
            assert fact_with_source.source.id is not None
            assert fact_with_source.source.content is not None
            assert fact_with_source.source.timestamp is not None
            assert isinstance(fact_with_source.source.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_get_entity_with_multiple_facts(
        self,
        get_entity_usecase: GetEntityUseCaseImpl,
        assimilate_knowledge_usecase: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test retrieving an entity with multiple facts from multiple assimilations."""

        # First assimilation
        first_content = "I live in Paris and work as a Software Engineer."
        first_request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content=first_content,
        )
        _ = await assimilate_knowledge_usecase.execute(first_request)

        # Second assimilation with same entity
        second_content = "I enjoy hiking and photography as hobbies."
        second_request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content=second_content,
        )
        _ = await assimilate_knowledge_usecase.execute(second_request)

        # Retrieve the entity
        result: GetEntityResponse = await get_entity_usecase.execute(
            identifier_value=test_identifier.value, identifier_type=test_identifier.type
        )

        # Assert
        assert result.entity is not None
        assert len(result.facts) > 1  # Should have facts from both assimilations

        # Verify all facts have proper structure
        fact_names: set[str] = set()
        for fact_with_source in result.facts:
            assert fact_with_source.fact.name
            assert fact_with_source.fact.type
            assert fact_with_source.fact.fact_id
            assert fact_with_source.relationship.verb
            # Source should always be present for facts created through assimilation
            assert fact_with_source.source is not None
            assert fact_with_source.source.id is not None
            assert fact_with_source.source.content is not None
            assert fact_with_source.source.timestamp is not None
            assert isinstance(fact_with_source.source.timestamp, datetime)
            fact_names.add(fact_with_source.fact.name)

        # Should have multiple distinct facts
        assert len(fact_names) > 1

    @pytest.mark.asyncio
    async def test_get_entity_not_found(
        self,
        get_entity_usecase: GetEntityUseCaseImpl,
    ) -> None:
        """Test that retrieving a non-existent entity raises HTTPException."""

        from fastapi import HTTPException

        # Try to get an entity that doesn't exist
        with pytest.raises(HTTPException) as exc_info:
            _ = await get_entity_usecase.execute(
                identifier_value="nonexistent@example.com", identifier_type="email"
            )

        # Assert
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_get_entity_different_identifier_types(
        self,
        get_entity_usecase: GetEntityUseCaseImpl,
        assimilate_knowledge_usecase: AssimilateKnowledgeUseCaseImpl,
        test_content: str,
    ) -> None:
        """Test retrieving entities with different identifier types."""

        # Create entity with phone identifier
        phone_identifier = IdentifierDto(
            value=f"+1234567890{uuid.uuid4().hex[:6]}", type="phone"
        )
        phone_request = AssimilateKnowledgeRequest(
            identifier=phone_identifier,
            content=test_content,
        )
        _ = await assimilate_knowledge_usecase.execute(phone_request)

        # Retrieve by phone identifier
        result: GetEntityResponse = await get_entity_usecase.execute(
            identifier_value=phone_identifier.value,
            identifier_type=phone_identifier.type,
        )

        # Assert
        assert result.entity is not None
        assert result.identifier.identifier.value == phone_identifier.value
        assert result.identifier.identifier.type == phone_identifier.type
        assert len(result.facts) > 0

    @pytest.mark.asyncio
    async def test_get_entity_entity_with_no_facts(
        self,
        get_entity_usecase: GetEntityUseCaseImpl,
        arcadedb_repository: ArcadedbRepository,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test retrieving an entity that exists but has no associated facts."""

        # Create entity manually without facts
        from app.features.graph.models import Entity, HasIdentifier, Identifier

        entity = Entity(id=uuid.uuid4())  # Will use default timestamp
        identifier = Identifier(value=test_identifier.value, type=test_identifier.type)
        relationship = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=identifier.value,
            is_primary=True,
        )  # Will use default timestamp

        _ = await arcadedb_repository.create_entity(entity, identifier, relationship)

        # Retrieve the entity
        result: GetEntityResponse = await get_entity_usecase.execute(
            identifier_value=test_identifier.value, identifier_type=test_identifier.type
        )

        # Assert
        assert result.entity is not None
        assert result.identifier is not None
        assert result.facts == []  # Should be empty list, not None

    @pytest.mark.asyncio
    async def test_get_entity_with_primary_identifier_selection(
        self,
        get_entity_usecase: GetEntityUseCaseImpl,
        arcadedb_repository: ArcadedbRepository,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test that when an entity has multiple identifiers, the primary one is returned."""

        # Create entity with multiple identifiers
        from app.features.graph.models import Entity, HasIdentifier, Identifier

        entity = Entity(id=uuid.uuid4())
        primary_identifier = Identifier(
            value=test_identifier.value, type=test_identifier.type
        )
        primary_relationship = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=primary_identifier.value,
            is_primary=True,
        )

        # Create the entity with primary identifier
        _ = await arcadedb_repository.create_entity(
            entity, primary_identifier, primary_relationship
        )

        # Add a secondary identifier manually
        secondary_identifier = Identifier(
            value=f"secondary.{uuid.uuid4().hex[:8]}@example.com", type="email"
        )
        secondary_relationship = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=secondary_identifier.value,
            is_primary=False,
        )

        # Add secondary identifier using SQL
        database_name = get_database_name()
        params = {
            "entity_id": str(entity.id),
            "identifier_value": secondary_identifier.value,
            "identifier_type": secondary_identifier.type,
            "is_primary": secondary_relationship.is_primary,
            "relationship_created_at": secondary_relationship.created_at.isoformat(),
        }

        transaction_script = """
        UPDATE Identifier
        SET value = :identifier_value, type = :identifier_type
        UPSERT WHERE value = :identifier_value AND type = :identifier_type;
        CREATE EDGE HAS_IDENTIFIER
        FROM (SELECT FROM Entity WHERE id = :entity_id)
        TO (SELECT FROM Identifier WHERE value = :identifier_value AND type = :identifier_type)
        SET is_primary = :is_primary,
            created_at = :relationship_created_at;
        """

        await arcadedb_repository.db.execute_command(
            transaction_script,
            database_name,
            parameters=params,
            language="sqlscript",
        )

        # Retrieve the entity by primary identifier
        result: GetEntityResponse = await get_entity_usecase.execute(
            identifier_value=test_identifier.value, identifier_type=test_identifier.type
        )

        # Assert that the primary identifier is returned
        assert result.identifier.identifier.value == test_identifier.value
        assert result.identifier.identifier.type == test_identifier.type
        assert result.identifier.relationship.is_primary is True
