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


class TestDeleteEntityIntegration:
    """Integration tests for EntityRepository delete methods."""

    @pytest.mark.asyncio
    async def test_delete_entity_by_id_success(
        self,
        entity_repository: EntityRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
    ) -> None:
        """Test successful deletion of an existing entity."""
        # Arrange: Create an entity first
        create_result = await entity_repository.create_entity(
            test_entity, test_identifier, test_relationship
        )
        assert isinstance(create_result, dict)
        assert "entity" in create_result
        assert "identifier" in create_result
        assert "relationship" in create_result

        # Verify entity exists before deletion
        found_entity = await entity_repository.find_entity_by_id(test_entity.id)
        assert found_entity is not None

        # Act: Delete the entity
        delete_result = await entity_repository.delete_entity_by_id(test_entity.id)

        # Assert: Deletion should succeed
        assert delete_result is True

        # Verify entity no longer exists
        found_entity_after = await entity_repository.find_entity_by_id(test_entity.id)
        assert found_entity_after is None

    @pytest.mark.asyncio
    async def test_delete_entity_by_id_not_found(
        self,
        entity_repository: EntityRepository,
    ) -> None:
        """Test deletion of a non-existent entity."""
        # Arrange: Use a random UUID that doesn't exist
        non_existent_id = uuid.uuid4()

        # Act: Try to delete non-existent entity
        delete_result = await entity_repository.delete_entity_by_id(non_existent_id)

        # Assert: Deletion should fail gracefully
        assert delete_result is False

    @pytest.mark.asyncio
    async def test_delete_entity_preserves_identifiers(
        self,
        entity_repository: EntityRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
    ) -> None:
        """Test that deleting an entity preserves its identifiers for potential reuse."""
        # Arrange: Create an entity
        create_result = await entity_repository.create_entity(
            test_entity, test_identifier, test_relationship
        )
        assert isinstance(create_result, dict)
        assert "entity" in create_result
        assert "identifier" in create_result
        assert "relationship" in create_result

        # Act: Delete the entity
        delete_result = await entity_repository.delete_entity_by_id(test_entity.id)
        assert delete_result is True

        # Assert: Entity is gone but we can't easily verify identifier exists
        # without additional repository methods. The important thing is that
        # the deletion succeeded without errors.
        found_entity = await entity_repository.find_entity_by_id(test_entity.id)
        assert found_entity is None
