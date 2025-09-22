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
async def test_my_test(arcadedb_repository, entity_cleanup_tracker):
    entity = Entity(metadata={"test_type": "my_test"})
    entity_cleanup_tracker(entity)  # Track for cleanup
    # ... create and test entity ...
    # Entity deleted immediately after this test
"""

import pytest

from app.features.graph.models import Entity
from app.features.graph.repositories.arcadedb_repository import ArcadedbRepository


@pytest.fixture
async def resource_tracker(arcadedb_repository: ArcadedbRepository):
    """Track resources created during a test for cleanup.

    This fixture provides a `track(resource)` function that can track
    any type of graph resource (Entity, Fact, Source) for cleanup.
    At the end of the test, all tracked resources are deleted.
    """
    created_resources: list[
        tuple[str, str]
    ] = []  # List of (resource_type, resource_id)

    def track_resource(resource):
        """Track a resource for later cleanup.

        Args:
            resource: The resource object to track (Entity, Fact, Source, etc.)
        """
        from app.features.graph.models import Fact, Source

        if isinstance(resource, Entity):
            created_resources.append(("entity", str(resource.id)))
        elif isinstance(resource, Fact):
            created_resources.append(("fact", resource.fact_id))
        elif isinstance(resource, Source):
            created_resources.append(("source", str(resource.id)))
        else:
            raise ValueError(f"Unsupported resource type: {type(resource)}")

    yield track_resource

    # Cleanup: Delete all tracked resources after test
    if created_resources:  # Only cleanup if there are resources to clean
        await _cleanup_resources(arcadedb_repository, created_resources)


async def _cleanup_resources(
    arcadedb_repository: ArcadedbRepository, resources: list[tuple[str, str]]
):
    """Helper function to cleanup resources asynchronously."""
    for resource_type, resource_id in resources:
        try:
            if resource_type == "entity":
                result = await arcadedb_repository.delete_entity_by_id(resource_id)
                action = "entity"
            elif resource_type == "fact":
                result = await arcadedb_repository.delete_fact_by_id(resource_id)
                action = "fact"
            elif resource_type == "source":
                result = await arcadedb_repository.delete_source_by_id(resource_id)
                action = "source"
            else:
                print(
                    f"Warning: Unknown resource type {resource_type} for {resource_id}"
                )
                continue

            if result:
                print(f"Cleaned up {action} {resource_id}")
            else:
                print(f"Warning: {action} {resource_id} was not found for cleanup")
        except Exception as e:
            print(f"Warning: Failed to cleanup {resource_type} {resource_id}: {e}")
