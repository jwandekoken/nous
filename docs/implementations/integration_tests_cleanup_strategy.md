# Integration Tests Cleanup Strategy

This document outlines the plan to implement a robust cleanup strategy for integration tests, ensuring that all created resources (Entities, Identifiers, Facts, Sources, etc.) are properly removed after each test run.

## Analysis of the Current Situation

Currently, the `entity_cleanup_tracker` in `integration_tests_utils.py` only tracks `Entity` objects and uses `arcadedb_repository.delete_entity_by_id()` for cleanup.

The current implementation of `delete_entity_by_id` in `arcadedb_repository.py` only deletes the `Entity` vertex. While ArcadeDB removes the connecting edges (`HAS_IDENTIFIER`, `HAS_FACT`), it does not delete the vertices at the other end of those edges, leading to orphaned `Identifier`, `Fact`, and `Source` vertices in the database after test runs.

## Proposed Plan: Repository-Driven Cleanup

The proposed solution is to enhance the `ArcadedbRepository` to handle all resource deletions correctly and then use this enhanced logic within a unified test fixture. This approach ensures that our tests validate the same deletion logic that would be used in a production environment.

The plan is divided into two phases:

### Phase 1: Enhance `ArcadedbRepository` with Complete Deletion Logic

1.  **Task: Implement Cascading Delete for Entities.**

    - **Goal:** The `delete_entity_by_id` method must correctly delete an entity and any associated `Identifier` or `Fact` vertices that would otherwise become orphaned.
    - **Action:** Modify `delete_entity_by_id` in `app/features/graph/repositories/arcadedb_repository.py` to use a `sqlscript` transaction. This atomic operation will:
      a. Find the `Entity` to be deleted.
      b. Find all `Identifier` vertices connected to it.
      c. For each `Identifier`, check if it's connected to any other `Entity`.
      d. Delete any `Identifier` that would become an orphan.
      e. Repeat the process for `Fact` vertices connected to the entity.
      f. Finally, delete the `Entity` vertex itself.

2.  **Task: Create Deletion Methods for `Fact` and `Source`.**
    - **Goal:** Provide methods to directly delete `Fact` and `Source` vertices, which is necessary for tests that create these resources independently.
    - **Action:** Add the following new methods to `GraphRepository`:
      - `delete_fact_by_id(fact_id: str) -> bool`: Deletes a `Fact` and any `Source` vertices that become orphans as a result.
      - `delete_source_by_id(source_id: str) -> bool`: Deletes a single `Source` vertex.

### Phase 2: Create a Unified Cleanup Fixture

3.  **Task: Evolve `entity_cleanup_tracker` into `resource_tracker`.**
    - **Goal:** Create a single, flexible fixture in `tests/features/graph/repositories/integration_tests_utils.py` that can track and clean up any type of resource created during tests.
    - **Action:** Replace `entity_cleanup_tracker` with a new fixture named `resource_tracker`.
      - It will provide a `track(resource)` function that identifies the type of resource (`Entity`, `Fact`, `Source`) and stores its unique ID for cleanup.
      - After each test completes, the fixture will iterate through the tracked IDs and call the appropriate deletion method from the enhanced `GraphRepository`.

## Example Usage in a Test

The new testing workflow will be cleaner and more straightforward:

```python
# Example of future test
import pytest
from app.features.graph.repositories.arcadedb_repository import ArcadedbRepository
from typing import Callable, Any

@pytest.mark.asyncio
async def test_create_entity_with_fact(
    arcadedb_repository: ArcadedbRepository,
    resource_tracker: Callable[[Any], None],
):
    # Arrange
    entity = Entity(...)
    resource_tracker(entity) # Track entity for cleanup

    # If a test creates a standalone fact, we would track it:
    fact = Fact(name="Paris", type="Location")
    resource_tracker(fact)

    # Act
    # ... test logic ...

# The resource_tracker fixture will automatically clean up the tracked entity
# and fact using the robust repository deletion methods.
```
