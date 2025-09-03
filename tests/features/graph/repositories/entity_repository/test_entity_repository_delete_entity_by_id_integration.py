"""Integration tests for EntityRepository using real database connection.

This module provides integration tests for the EntityRepository
using the actual production database connection.

CLEANUP MECHANISMS:
==================

This test file implements multiple cleanup strategies:

1. TEST-LEVEL CLEANUP (Primary):
   - `entity_cleanup_tracker` fixture: Track specific entities for cleanup after each test
   - Uses existing `delete_entity_by_id()` method for reliable cleanup
   - Handles event loop conflicts gracefully with fallback mechanisms

2. MANUAL CLEANUP (For debugging):
   - `clear_test_data()` method: Removes only test data (safe)
   - Call manually when needed: `await repo.clear_test_data()`
   - Identifies test entities by metadata.test_type field

Note: Session-level cleanup was removed to avoid event loop conflicts with pytest.

USAGE EXAMPLES:
==============

# Using test-level tracking (recommended):
@pytest.mark.asyncio
async def test_my_test(entity_repository, entity_cleanup_tracker):
    entity = Entity(metadata={"test_type": "my_test"})
    entity_cleanup_tracker(entity)  # Track for cleanup
    # ... create and test entity ...
    # Entity deleted immediately after this test

# Without tracking (manual cleanup needed):
@pytest.mark.asyncio
async def test_my_test(entity_repository):
    entity = Entity(metadata={"test_type": "my_test"})
    # ... create and test entity ...
    # Remember to clean up manually if needed

# Manual cleanup for debugging:
@pytest.mark.asyncio
async def test_debugging_scenario(entity_repository):
    # ... create test data ...
    # Clean up manually if needed
    await entity_repository.clear_test_data()
"""

import uuid
from typing import Callable

import pytest

from app.db.graph import GraphDB, get_graph_db, reset_graph_db
from app.features.graph.models import Entity, HasIdentifier, Identifier
from app.features.graph.repositories.entity_repository import EntityRepository

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
        _ = await entity_repository.create_entity(
            test_entity, test_identifier, test_relationship
        )

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
    async def test_delete_entity_deletes_unused_identifiers(
        self,
        entity_repository: EntityRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
    ) -> None:
        """Test that deleting an entity also deletes its identifiers if they're not used by other entities."""
        # Arrange: Create an entity
        _ = await entity_repository.create_entity(
            test_entity, test_identifier, test_relationship
        )

        # Act: Delete the entity
        delete_result = await entity_repository.delete_entity_by_id(test_entity.id)
        assert delete_result is True

        # Assert: Entity is gone
        found_entity = await entity_repository.find_entity_by_id(test_entity.id)
        assert found_entity is None

        # @TODO: improve this test to use the same identifier to create another entity

    @pytest.mark.asyncio
    async def test_delete_entity_preserves_shared_identifiers(
        self,
        entity_repository: EntityRepository,
        entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    ) -> None:
        """Test that deleting an entity preserves identifiers that are shared with other entities."""
        # Arrange: Create two entities that share the same identifier
        entity1 = Entity(metadata={"test_type": "shared_identifier", "entity": "1"})
        entity2 = Entity(metadata={"test_type": "shared_identifier", "entity": "2"})
        shared_identifier = Identifier(
            value=f"shared.test.{uuid.uuid4()}@example.com", type="email"
        )

        # Track entities for cleanup (optional - session cleanup will handle these too)
        entity_cleanup_tracker(entity1)
        entity_cleanup_tracker(entity2)

        # Create first entity
        relationship1 = HasIdentifier(
            from_entity_id=entity1.id,
            to_identifier_value=shared_identifier.value,
            is_primary=True,
        )
        _ = await entity_repository.create_entity(
            entity1, shared_identifier, relationship1
        )

        # Create second entity with same identifier (this will reuse the existing identifier)
        relationship2 = HasIdentifier(
            from_entity_id=entity2.id,
            to_identifier_value=shared_identifier.value,
            is_primary=True,
        )
        _ = await entity_repository.create_entity(
            entity2, shared_identifier, relationship2
        )

        # Act: Delete the first entity
        delete_result = await entity_repository.delete_entity_by_id(entity1.id)
        assert delete_result is True

        # Assert: First entity is gone
        found_entity1 = await entity_repository.find_entity_by_id(entity1.id)
        assert found_entity1 is None

        # Assert: Second entity still exists and still has the identifier
        found_entity2 = await entity_repository.find_entity_by_id(entity2.id)
        assert found_entity2 is not None
        assert found_entity2["identifiers"][0].value == shared_identifier.value
        assert found_entity2["identifiers"][0].type == shared_identifier.type
