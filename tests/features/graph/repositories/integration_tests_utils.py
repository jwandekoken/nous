"""Integration test utilities for database cleanup and common fixtures.

This module provides reusable utilities for integration tests that work with
the GraphRepository and graph database.

CLEANUP MECHANISMS:
==================

TEST-LEVEL CLEANUP (Primary):
   - `entity_cleanup_tracker` fixture: Track specific entities for cleanup after each test
   - Uses existing `delete_entity_by_id()` method for reliable cleanup

USAGE EXAMPLES:
==============

# Using test-level tracking:
@pytest.mark.asyncio
async def test_my_test(graph_repository, entity_cleanup_tracker):
    entity = Entity(metadata={"test_type": "my_test"})
    entity_cleanup_tracker(entity)  # Track for cleanup
    # ... create and test entity ...
    # Entity deleted immediately after this test
"""

import uuid

import pytest

from app.features.graph.models import Entity
from app.features.graph.repositories.graph_repository import GraphRepository


@pytest.fixture
async def entity_cleanup_tracker(graph_repository: GraphRepository):
    """Track entities created during a test for cleanup."""
    created_entities: list[uuid.UUID] = []

    def track_entity(entity: Entity):
        """Track an entity for later cleanup."""
        created_entities.append(entity.id)

    yield track_entity

    # Cleanup: Delete all tracked entities after test
    if created_entities:  # Only cleanup if there are entities to clean
        await _cleanup_entities(graph_repository, created_entities)


async def _cleanup_entities(
    graph_repository: GraphRepository, entity_ids: list[uuid.UUID]
):
    """Helper function to cleanup entities asynchronously."""
    for entity_id in entity_ids:
        try:
            result = await graph_repository.delete_entity_by_id(str(entity_id))
            if result:
                print(f"Cleaned up entity {entity_id}")
        except Exception as e:
            print(f"Warning: Failed to cleanup entity {entity_id}: {e}")
