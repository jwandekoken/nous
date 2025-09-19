"""Integration tests for GraphRepository using real database connection.

This module provides integration tests for the GraphRepository
using the actual production database connection.
"""

import uuid
from typing import Callable

import pytest

from app.db.arcadedb import GraphDB, get_database_name, get_graph_db, reset_graph_db
from app.features.graph.models import Entity, HasIdentifier, Identifier
from app.features.graph.repositories.graph_repository import (
    CreateEntityResult,
    GraphRepository,
)

# Import cleanup utilities
from tests.features.graph.repositories.integration_tests_utils import (
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
async def graph_repository(graph_db: GraphDB) -> GraphRepository:
    """GraphRepository instance for testing."""
    return GraphRepository(graph_db)


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


class TestGraphRepositoryIntegration:
    """Integration tests for GraphRepository create_entity method."""

    @pytest.mark.asyncio
    async def test_create_entity_basic(
        self,
        graph_repository: GraphRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
        entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    ) -> None:
        """Test basic entity creation with minimal data."""
        # Track entity for cleanup
        entity_cleanup_tracker(test_entity)

        # Act
        result: CreateEntityResult = await graph_repository.create_entity(
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

    @pytest.mark.asyncio
    async def test_find_entity_by_identifier(
        self,
        graph_repository: GraphRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
        entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    ) -> None:
        """Test finding an entity by its identifier value and type."""
        # Track entity for cleanup
        entity_cleanup_tracker(test_entity)

        # First create the entity with identifier
        _ = await graph_repository.create_entity(
            test_entity, test_identifier, test_relationship
        )

        # Act - Find the entity by identifier
        find_result = await graph_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )

        # Assert
        assert find_result is not None
        assert isinstance(find_result, dict)
        assert "entity" in find_result
        assert "identifier" in find_result
        assert "relationship" in find_result

        # Verify returned objects have correct properties
        found_entity = find_result["entity"]
        found_identifier = find_result["identifier"]
        found_relationship = find_result["relationship"]

        assert isinstance(found_entity, Entity)
        assert isinstance(found_identifier, Identifier)
        assert isinstance(found_relationship, HasIdentifier)

        # Check that we found the correct entity and identifier
        assert found_entity.id == test_entity.id
        assert found_entity.metadata == test_entity.metadata
        assert found_identifier.value == test_identifier.value
        assert found_identifier.type == test_identifier.type
        assert found_relationship.is_primary == test_relationship.is_primary
        assert found_relationship.from_entity_id == test_entity.id
        assert found_relationship.to_identifier_value == test_identifier.value

    @pytest.mark.asyncio
    async def test_find_entity_by_id(
        self,
        graph_repository: GraphRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
        entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    ) -> None:
        """Test finding an entity by its ID."""
        # Track entity for cleanup
        entity_cleanup_tracker(test_entity)

        # First create the entity with identifier
        _ = await graph_repository.create_entity(
            test_entity, test_identifier, test_relationship
        )

        # Act - Find the entity by its ID
        find_result = await graph_repository.find_entity_by_id(str(test_entity.id))

        # Assert
        assert find_result is not None
        assert isinstance(find_result, dict)
        assert "entity" in find_result
        assert "identifiers" in find_result
        assert "facts_with_sources" in find_result

        # Verify returned objects have correct properties
        found_entity = find_result["entity"]
        found_identifiers = find_result["identifiers"]
        found_facts_with_sources = find_result["facts_with_sources"]

        assert isinstance(found_entity, Entity)
        assert isinstance(found_identifiers, list)
        assert isinstance(found_facts_with_sources, list)

        # Check that we found the correct entity
        assert found_entity.id == test_entity.id
        assert found_entity.metadata == test_entity.metadata

        # Check that we found the correct identifier
        assert len(found_identifiers) == 1
        found_identifier = found_identifiers[0]
        assert isinstance(found_identifier, Identifier)
        assert found_identifier.value == test_identifier.value
        assert found_identifier.type == test_identifier.type

        # Check that facts with sources is empty (for now)
        assert len(found_facts_with_sources) == 0

    @pytest.mark.asyncio
    async def test_find_entity_by_id_no_identifiers(
        self,
        graph_repository: GraphRepository,
        test_entity: Entity,
        entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    ) -> None:
        """Test finding an entity by its ID when it has no identifiers."""
        # Track entity for cleanup
        entity_cleanup_tracker(test_entity)

        # Create entity without identifier (we'll create it manually)
        # Use a simple SQL query to create just the entity vertex
        database_name = get_database_name()
        db = await get_graph_db()
        create_query = f"""
        CREATE VERTEX Entity
        SET id = '{test_entity.id}',
            created_at = '{test_entity.created_at.isoformat()}',
            metadata = {test_entity.metadata or {}}
        """

        await db.execute_command(create_query, database_name, language="sql")

        # Act - Find the entity by its ID
        find_result = await graph_repository.find_entity_by_id(str(test_entity.id))

        # Assert
        assert find_result is not None
        assert isinstance(find_result, dict)
        assert "entity" in find_result
        assert "identifiers" in find_result
        assert "facts_with_sources" in find_result

        # Verify returned objects have correct properties
        found_entity = find_result["entity"]
        found_identifiers = find_result["identifiers"]
        found_facts_with_sources = find_result["facts_with_sources"]

        assert isinstance(found_entity, Entity)
        assert isinstance(found_identifiers, list)
        assert isinstance(found_facts_with_sources, list)

        # Check that we found the correct entity
        assert found_entity.id == test_entity.id
        assert found_entity.metadata == test_entity.metadata

        # Check that identifiers list is empty (no identifiers)
        assert len(found_identifiers) == 0

        # Check that facts with sources is empty (for now)
        assert len(found_facts_with_sources) == 0

    @pytest.mark.asyncio
    async def test_find_entity_by_id_not_found(
        self,
        graph_repository: GraphRepository,
    ) -> None:
        """Test finding an entity by ID when it doesn't exist."""
        # Act - Try to find a non-existent entity
        find_result = await graph_repository.find_entity_by_id("non-existent-id")

        # Assert
        assert find_result is None

    @pytest.mark.asyncio
    async def test_find_entity_by_id_empty_id(
        self,
        graph_repository: GraphRepository,
    ) -> None:
        """Test finding an entity with empty ID raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Entity ID cannot be empty"):
            _ = await graph_repository.find_entity_by_id("")

    @pytest.mark.asyncio
    async def test_delete_entity_by_id(
        self,
        graph_repository: GraphRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
        entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    ) -> None:
        """Test deleting an entity by its ID."""
        # Track entity for cleanup (though we'll delete it manually)
        entity_cleanup_tracker(test_entity)

        # First create the entity with identifier
        _ = await graph_repository.create_entity(
            test_entity, test_identifier, test_relationship
        )

        # Verify the entity exists by finding it
        found_before = await graph_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert found_before is not None

        # Act - Delete the entity by its ID
        delete_result = await graph_repository.delete_entity_by_id(str(test_entity.id))

        # Assert
        assert delete_result is True

        # Verify the entity was actually deleted
        found_after = await graph_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert found_after is None  # Should not find the entity anymore

    @pytest.mark.asyncio
    async def test_delete_entity_by_id_not_found(
        self,
        graph_repository: GraphRepository,
    ) -> None:
        """Test deleting an entity that doesn't exist."""
        # Act - Try to delete a non-existent entity
        delete_result = await graph_repository.delete_entity_by_id("non-existent-id")

        # Assert
        assert delete_result is False

    @pytest.mark.asyncio
    async def test_delete_entity_with_shared_identifier(
        self,
        graph_repository: GraphRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_relationship: HasIdentifier,
        entity_cleanup_tracker: Callable[[Entity], None],  # noqa: F811
    ) -> None:
        """Test that identifiers shared by multiple entities are not deleted."""
        # Track entity for cleanup
        entity_cleanup_tracker(test_entity)

        # Create first entity with identifier
        _ = await graph_repository.create_entity(
            test_entity, test_identifier, test_relationship
        )

        # Create second entity with the same identifier
        second_entity = Entity(metadata={"test_type": "shared_identifier_test"})
        second_relationship = HasIdentifier(
            from_entity_id=second_entity.id,
            to_identifier_value=test_identifier.value,
            is_primary=True,
        )
        _ = await graph_repository.create_entity(
            second_entity, test_identifier, second_relationship
        )

        # Track second entity for cleanup too
        entity_cleanup_tracker(second_entity)

        # Delete the first entity
        delete_result = await graph_repository.delete_entity_by_id(str(test_entity.id))
        assert delete_result is True

        # Verify first entity is gone
        found_first = await graph_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert found_first is not None  # Should still find the second entity

        # Clean up second entity
        _ = await graph_repository.delete_entity_by_id(str(second_entity.id))
