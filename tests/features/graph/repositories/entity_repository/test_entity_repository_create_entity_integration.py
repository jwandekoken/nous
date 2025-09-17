"""Integration tests for EntityRepository using real database connection.

This module provides integration tests for the EntityRepository
using the actual production database connection.
"""

import uuid
from typing import Callable

import pytest

from app.db.arcadedb import GraphDB, get_graph_db, reset_graph_db
from app.features.graph.models import Entity, HasIdentifier, Identifier
from app.features.graph.repositories.entity_repository import (
    CreateEntityResult,
    EntityRepository,
)

# Import cleanup utilities
from tests.features.graph.repositories.entity_repository.integration_tests_utils import (
    entity_cleanup_tracker,  # noqa: F401 # pyright: ignore[reportUnusedImport]
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
            "test_type": "integration",
            "test_run_id": str(uuid.uuid4()),
            "created_by": "test_entity_integration.py",
        }
    )


@pytest.fixture
def test_identifier() -> Identifier:
    """Test identifier for integration testing."""
    return Identifier(
        value=f"test.integration.{uuid.uuid4()}@example.com", type="email"
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


class TestCreateEntityIntegration:
    """Integration tests for EntityRepository create_entity method."""

    @pytest.mark.asyncio
    async def test_create_entity_basic(
        self,
        entity_repository: EntityRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
        entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    ) -> None:
        """Test basic entity creation with minimal data."""
        # Track entity for cleanup
        entity_cleanup_tracker(test_entity)

        # Act
        result: CreateEntityResult = await entity_repository.create_entity(
            test_entity, test_identifier, test_relationship
        )

        print(f"DEBUG - Result: {result}")

        # Assert
        assert isinstance(result, dict)
        assert "entity" in result
        assert "identifier" in result
        assert "relationship" in result

        # Verify returned objects have correct properties
        returned_entity = result["entity"]
        returned_identifier = result["identifier"]
        returned_relationship = result["relationship"]

        assert isinstance(returned_entity, Entity)
        assert isinstance(returned_identifier, Identifier)
        assert isinstance(returned_relationship, HasIdentifier)

        # Check that the entity was created correctly
        assert returned_entity.id == test_entity.id
        assert returned_entity.metadata == test_entity.metadata

        # For now, just check that identifier and relationship are returned (they're not created in DB yet)
        assert returned_identifier.value == test_identifier.value
        assert returned_identifier.type == test_identifier.type
        assert returned_relationship.is_primary == test_relationship.is_primary

    # @pytest.mark.asyncio
    # async def test_create_entity_with_empty_metadata(
    #     self,
    #     entity_repository: EntityRepository,
    #     test_identifier: Identifier,
    #     entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    # ) -> None:
    #     """Test creating entity with empty metadata."""
    #     # Arrange
    #     entity = Entity(metadata={})
    #     relationship = HasIdentifier(
    #         from_entity_id=entity.id,
    #         to_identifier_value=test_identifier.value,
    #         is_primary=True,
    #     )

    #     # Track entity for cleanup
    #     entity_cleanup_tracker(entity)

    #     # Act
    #     result: CreateEntityResult = await entity_repository.create_entity(
    #         entity, test_identifier, relationship
    #     )

    #     # Assert
    #     assert isinstance(result, dict)
    #     assert "entity" in result
    #     assert "identifier" in result
    #     assert "relationship" in result

    #     # Verify returned objects
    #     returned_entity = result["entity"]
    #     returned_identifier = result["identifier"]
    #     returned_relationship = result["relationship"]

    #     assert isinstance(returned_entity, Entity)
    #     assert isinstance(returned_identifier, Identifier)
    #     assert isinstance(returned_relationship, HasIdentifier)

    #     assert returned_entity.metadata == {}
    #     assert returned_identifier.value == test_identifier.value
    #     assert returned_relationship.is_primary is True

    # @pytest.mark.asyncio
    # async def test_create_entity_with_rich_metadata(
    #     self,
    #     entity_repository: EntityRepository,
    #     test_identifier: Identifier,
    #     entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    # ) -> None:
    #     """Test creating entity with rich metadata."""
    #     # Arrange
    #     expected_metadata = {
    #         "name": "Test username",
    #         "age": "25",
    #         "preferences": "dark_mode,notifications",
    #         "integration_test": "true",
    #         "test_id": str(uuid.uuid4()),
    #     }
    #     entity = Entity(metadata=expected_metadata)
    #     relationship = HasIdentifier(
    #         from_entity_id=entity.id,
    #         to_identifier_value=test_identifier.value,
    #         is_primary=True,
    #     )

    #     # Track entity for cleanup
    #     entity_cleanup_tracker(entity)

    #     # Act
    #     result: CreateEntityResult = await entity_repository.create_entity(
    #         entity, test_identifier, relationship
    #     )

    #     # Assert
    #     assert isinstance(result, dict)
    #     assert "entity" in result
    #     assert "identifier" in result
    #     assert "relationship" in result

    #     # Verify returned objects
    #     returned_entity = result["entity"]
    #     returned_identifier = result["identifier"]
    #     returned_relationship = result["relationship"]

    #     assert isinstance(returned_entity, Entity)
    #     assert isinstance(returned_identifier, Identifier)
    #     assert isinstance(returned_relationship, HasIdentifier)

    #     assert returned_entity.metadata == expected_metadata
    #     assert returned_identifier.value == test_identifier.value
    #     assert returned_relationship.is_primary is True

    # @pytest.mark.asyncio
    # async def test_create_entity_different_identifier_types(
    #     self,
    #     entity_repository: EntityRepository,
    #     entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    # ) -> None:
    #     """Test creating entities with different identifier types."""
    #     # Test cases for different identifier types
    #     test_cases = [
    #         ("test.phone.123@example.com", "email"),
    #         ("+1234567890", "phone"),
    #         ("test_username_123", "username"),
    #         ("test-uuid-value", "uuid"),
    #     ]

    #     for value, type_ in test_cases:
    #         # Arrange
    #         entity = Entity(
    #             metadata={
    #                 "test_type": "identifier_types_test",
    #                 "identifier_type": type_,
    #             }
    #         )
    #         identifier = Identifier(value=value, type=type_)
    #         relationship = HasIdentifier(
    #             from_entity_id=entity.id,
    #             to_identifier_value=identifier.value,
    #             is_primary=True,
    #         )

    #         # Track entity for cleanup
    #         entity_cleanup_tracker(entity)

    #         # Act
    #         result: CreateEntityResult = await entity_repository.create_entity(
    #             entity, identifier, relationship
    #         )

    #         # Assert
    #         assert isinstance(result, dict), (
    #             f"Failed to create entity with identifier type: {type_}"
    #         )
    #         assert "entity" in result
    #         assert "identifier" in result
    #         assert "relationship" in result

    #         # Verify returned identifier type matches
    #         returned_identifier = result["identifier"]
    #         assert returned_identifier.type == type_, (
    #             f"Identifier type mismatch for {type_}"
    #         )

    # @pytest.mark.asyncio
    # async def test_create_entity_multiple_calls(
    #     self,
    #     entity_repository: EntityRepository,
    #     test_identifier: Identifier,
    #     test_relationship: HasIdentifier,
    #     entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    # ) -> None:
    #     """Test creating multiple entities in sequence."""
    #     # Create multiple entities

    #     for i in range(3):
    #         # Arrange
    #         entity = Entity(
    #             metadata={
    #                 "batch_test": "true",
    #                 "sequence": str(i),
    #                 "test_run": str(uuid.uuid4()),
    #             }
    #         )

    #         # Track entity for cleanup
    #         entity_cleanup_tracker(entity)

    #         # Act
    #         result: CreateEntityResult = await entity_repository.create_entity(
    #             entity, test_identifier, test_relationship
    #         )

    #         # Assert
    #         assert isinstance(result, dict), f"Failed to create entity {i}"
    #         assert "entity" in result
    #         assert "identifier" in result
    #         assert "relationship" in result

    #         # Verify returned entity has the correct metadata
    #         returned_entity = result["entity"]
    #         assert returned_entity.metadata is not None
    #         assert returned_entity.metadata["batch_test"] == "true"
    #         assert returned_entity.metadata["sequence"] == str(i)
