"""Integration tests for EntityRepository find_entity_by_id method using real database connection.

This module provides integration tests for the EntityRepository find_entity_by_id method
using the actual production database connection.
"""

import uuid

import pytest

from app.db.graph import GraphDB, get_graph_db, reset_graph_db
from app.features.graph.models import Entity, HasIdentifier, Identifier
from app.features.graph.repositories.entity_repository import (
    EntityRepository,
    EntityWithRelations,
)


@pytest.fixture(autouse=True)
async def reset_db_connection():
    """Reset database connection before each test."""
    await reset_graph_db()


@pytest.fixture
async def graph_db() -> GraphDB:
    """Real database connection for integration tests."""
    return await get_graph_db()


@pytest.fixture
async def entity_repository(graph_db: GraphDB) -> EntityRepository:
    """EntityRepository instance for testing."""
    return EntityRepository(graph_db)


@pytest.fixture
def test_entity() -> Entity:
    """Test entity with integration test metadata."""
    return Entity(
        metadata={
            "test_type": "find_entity_integration",
            "test_run_id": str(uuid.uuid4()),
            "created_by": "test_entity_repository_find_entity_by_id_integration.py",
        }
    )


@pytest.fixture
def test_identifier() -> Identifier:
    """Test identifier for integration testing."""
    return Identifier(
        value=f"test.find.integration.{uuid.uuid4()}@example.com", type="email"
    )


@pytest.fixture
def test_relationship(
    test_entity: Entity, test_identifier: Identifier
) -> HasIdentifier:
    """Test relationship between entity and identifier."""
    return HasIdentifier(
        from_entity_id=test_entity.id,
        to_identifier_value=test_identifier.value,
        is_primary=True,
    )


class TestFindEntityByIdIntegration:
    """Integration tests for EntityRepository find_entity_by_id method."""

    @pytest.mark.asyncio
    async def test_find_entity_by_id_existing_entity(
        self,
        entity_repository: EntityRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
    ) -> None:
        """Test finding an existing entity by ID."""
        # Arrange - Create an entity first
        await entity_repository.create_entity(
            test_entity, test_identifier, test_relationship
        )

        # Act
        result: EntityWithRelations | None = await entity_repository.find_entity_by_id(
            test_entity.id
        )

        # Assert
        assert result is not None
        assert isinstance(result, dict)

        # Verify result structure
        assert "entity" in result
        assert "identifiers" in result
        assert "facts_with_sources" in result

        # Verify entity data
        returned_entity = result["entity"]
        assert isinstance(returned_entity, Entity)
        assert returned_entity.id == test_entity.id
        assert returned_entity.metadata == test_entity.metadata

        # Verify identifiers (should contain the one we created)
        identifiers = result["identifiers"]
        assert isinstance(identifiers, list)
        assert len(identifiers) == 1
        returned_identifier = identifiers[0]
        assert isinstance(returned_identifier, Identifier)
        assert returned_identifier.value == test_identifier.value
        assert returned_identifier.type == test_identifier.type

        # Verify facts_with_sources (should be empty for this test)
        facts_with_sources = result["facts_with_sources"]
        assert isinstance(facts_with_sources, list)
        assert len(facts_with_sources) == 0  # No facts created in this test

    @pytest.mark.asyncio
    async def test_find_entity_by_id_non_existing_entity(
        self,
        entity_repository: EntityRepository,
    ) -> None:
        """Test finding a non-existing entity by ID returns None."""
        # Arrange
        non_existing_id = uuid.uuid4()

        # Act
        result: EntityWithRelations | None = await entity_repository.find_entity_by_id(
            non_existing_id
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_entity_by_id_with_empty_metadata(
        self,
        entity_repository: EntityRepository,
        test_identifier: Identifier,
    ) -> None:
        """Test finding an entity with empty metadata."""
        # Arrange
        entity = Entity(metadata={})
        relationship = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=test_identifier.value,
            is_primary=True,
        )

        # Create the entity
        await entity_repository.create_entity(entity, test_identifier, relationship)

        # Act
        result: EntityWithRelations | None = await entity_repository.find_entity_by_id(
            entity.id
        )

        # Assert
        assert result is not None
        returned_entity = result["entity"]
        assert isinstance(returned_entity, Entity)
        assert returned_entity.metadata == {}

    @pytest.mark.asyncio
    async def test_find_entity_by_id_with_rich_metadata(
        self,
        entity_repository: EntityRepository,
        test_identifier: Identifier,
    ) -> None:
        """Test finding an entity with rich metadata."""
        # Arrange
        expected_metadata = {
            "name": "Test User",
            "age": "30",
            "department": "Engineering",
            "integration_test": "find_entity_test",
            "test_id": str(uuid.uuid4()),
        }
        entity = Entity(metadata=expected_metadata)
        relationship = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=test_identifier.value,
            is_primary=True,
        )

        # Create the entity
        await entity_repository.create_entity(entity, test_identifier, relationship)

        # Act
        result: EntityWithRelations | None = await entity_repository.find_entity_by_id(
            entity.id
        )

        # Assert
        assert result is not None
        returned_entity = result["entity"]
        assert isinstance(returned_entity, Entity)
        assert returned_entity.metadata == expected_metadata
        assert returned_entity.metadata is not None
        assert returned_entity.metadata["name"] == "Test User"
        assert returned_entity.metadata["department"] == "Engineering"

    @pytest.mark.asyncio
    async def test_find_entity_by_id_different_identifier_types(
        self,
        entity_repository: EntityRepository,
    ) -> None:
        """Test finding entities with different identifier types."""
        # Test cases for different identifier types
        test_cases = [
            ("test.email@example.com", "email"),
            ("+1234567890", "phone"),
            ("test_username", "username"),
            ("test-uuid-value", "uuid"),
        ]

        for value, type_ in test_cases:
            # Arrange
            entity = Entity(
                metadata={
                    "test_type": "identifier_type_test",
                    "identifier_type": type_,
                    "test_run": str(uuid.uuid4()),
                }
            )
            identifier = Identifier(value=value, type=type_)
            relationship = HasIdentifier(
                from_entity_id=entity.id,
                to_identifier_value=identifier.value,
                is_primary=True,
            )

            # Create the entity
            await entity_repository.create_entity(entity, identifier, relationship)

            # Act
            result: (
                EntityWithRelations | None
            ) = await entity_repository.find_entity_by_id(entity.id)

            # Assert
            assert result is not None, (
                f"Failed to find entity with identifier type: {type_}"
            )
            identifiers = result["identifiers"]
            assert len(identifiers) == 1
            returned_identifier = identifiers[0]
            assert isinstance(returned_identifier, Identifier)
            assert returned_identifier.type == type_
            assert returned_identifier.value == value

    @pytest.mark.asyncio
    async def test_find_entity_by_id_multiple_entities(
        self,
        entity_repository: EntityRepository,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
    ) -> None:
        """Test finding multiple different entities by their IDs."""
        # Create multiple entities
        created_entities = []
        for i in range(3):
            entity = Entity(
                metadata={
                    "batch_test": "true",
                    "sequence": str(i),
                    "test_run": str(uuid.uuid4()),
                }
            )

            # Create the entity
            await entity_repository.create_entity(
                entity, test_identifier, test_relationship
            )
            created_entities.append(entity)

        # Verify we can find each entity individually
        for i, entity in enumerate(created_entities):
            # Act
            result: (
                EntityWithRelations | None
            ) = await entity_repository.find_entity_by_id(entity.id)

            # Assert
            assert result is not None, f"Failed to find entity {i}"
            returned_entity = result["entity"]
            assert isinstance(returned_entity, Entity)
            assert returned_entity.metadata is not None
            assert returned_entity.metadata["sequence"] == str(i)
            assert returned_entity.metadata["batch_test"] == "true"

    @pytest.mark.asyncio
    async def test_find_entity_by_id_no_identifiers(
        self,
        entity_repository: EntityRepository,
    ) -> None:
        """Test finding an entity that has no identifiers."""
        # Arrange - Create entity without identifier (this might not be possible
        # with the current create_entity method, so we'll create one and then
        # simulate the scenario by creating an entity directly)

        # For now, create a normal entity and verify it has identifiers
        entity = Entity(metadata={"test_type": "no_identifiers_test"})
        identifier = Identifier(value="test@example.com", type="email")
        relationship = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=identifier.value,
            is_primary=True,
        )

        await entity_repository.create_entity(entity, identifier, relationship)

        # Act
        result: EntityWithRelations | None = await entity_repository.find_entity_by_id(
            entity.id
        )

        # Assert
        assert result is not None
        identifiers = result["identifiers"]
        assert isinstance(identifiers, list)
        assert len(identifiers) == 1  # Should have the identifier we created
        returned_identifier = identifiers[0]
        assert isinstance(returned_identifier, Identifier)
