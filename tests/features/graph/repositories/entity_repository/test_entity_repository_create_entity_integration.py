"""Integration tests for EntityRepository using real database connection.

This module provides integration tests for the EntityRepository
using the actual production database connection.
"""

import uuid

import pytest

from app.db.graph import GraphDB, get_graph_db
from app.features.graph.models import Entity, HasIdentifier, Identifier
from app.features.graph.repositories.entity_repository import EntityRepository


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
    ) -> None:
        """Test basic entity creation with minimal data."""
        # Act
        result = await entity_repository.create_entity(
            test_entity, test_identifier, test_relationship
        )

        print(f"DEBUG - Result: {result}")

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_create_entity_with_empty_metadata(
        self,
        entity_repository: EntityRepository,
        test_identifier: Identifier,
    ) -> None:
        """Test creating entity with empty metadata."""
        # Arrange
        entity = Entity(metadata={})
        relationship = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=test_identifier.value,
            is_primary=True,
        )

        # Act
        result = await entity_repository.create_entity(
            entity, test_identifier, relationship
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_create_entity_with_rich_metadata(
        self,
        entity_repository: EntityRepository,
        test_identifier: Identifier,
    ) -> None:
        """Test creating entity with rich metadata."""
        # Arrange
        entity = Entity(
            metadata={
                "name": "Test username",
                "age": "25",
                "preferences": "dark_mode,notifications",
                "integration_test": "true",
                "test_id": str(uuid.uuid4()),
            }
        )
        relationship = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=test_identifier.value,
            is_primary=True,
        )

        # Act
        result = await entity_repository.create_entity(
            entity, test_identifier, relationship
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_create_entity_different_identifier_types(
        self,
        entity_repository: EntityRepository,
        test_entity: Entity,
    ) -> None:
        """Test creating entities with different identifier types."""
        # Test cases for different identifier types
        test_cases = [
            ("test.phone.123@example.com", "email"),
            ("+1234567890", "phone"),
            ("test_username_123", "username"),
            ("test-uuid-value", "uuid"),
        ]

        for value, type_ in test_cases:
            # Arrange
            identifier = Identifier(value=value, type=type_)
            relationship = HasIdentifier(
                from_entity_id=test_entity.id,
                to_identifier_value=identifier.value,
                is_primary=True,
            )

            # Act
            result = await entity_repository.create_entity(
                test_entity, identifier, relationship
            )

            # Assert
            assert result is True, (
                f"Failed to create entity with identifier type: {type_}"
            )

    @pytest.mark.asyncio
    async def test_create_entity_multiple_calls(
        self,
        entity_repository: EntityRepository,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
    ) -> None:
        """Test creating multiple entities in sequence."""
        # Create multiple entities
        for i in range(3):
            # Arrange
            entity = Entity(
                metadata={
                    "batch_test": "true",
                    "sequence": str(i),
                    "test_run": str(uuid.uuid4()),
                }
            )

            # Act
            result = await entity_repository.create_entity(
                entity, test_identifier, test_relationship
            )

            # Assert
            assert result is True, f"Failed to create entity {i}"
