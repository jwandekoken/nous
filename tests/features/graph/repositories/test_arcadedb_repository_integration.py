"""Integration tests for ArcadedbRepository using real database connection.

This module provides integration tests for the ArcadedbRepository
using the actual production database connection.
"""

import uuid
from datetime import datetime
from typing import TypedDict

import pytest

from app.db.arcadedb import GraphDB, get_database_name, get_graph_db, reset_graph_db
from app.features.graph.models import (
    DerivedFrom,
    Entity,
    Fact,
    HasFact,
    HasIdentifier,
    Identifier,
    Source,
)
from app.features.graph.repositories.arcadedb_repository import (
    AddFactToEntityResult,
    ArcadedbRepository,
    CreateEntityResult,
)


class _TestFactItem(TypedDict):
    """Test fact item structure."""

    fact: Fact
    source: Source
    verb: str


@pytest.fixture(autouse=True)
async def reset_db_connection():
    """Reset database connection before each test."""
    await reset_graph_db()


@pytest.fixture
async def graph_db() -> GraphDB:
    """Real database connection for integration tests."""
    return await get_graph_db()


@pytest.fixture
async def arcadedb_repository(graph_db: GraphDB) -> ArcadedbRepository:
    """ArcadedbRepository instance for testing."""
    return ArcadedbRepository(graph_db)


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
def test_has_identifier_relationship(
    test_entity: Entity, test_identifier: Identifier
) -> HasIdentifier:
    """Test HasIdentifier relationship between entity and identifier."""
    return HasIdentifier(
        from_entity_id=test_entity.id,
        to_identifier_value=test_identifier.value,
        is_primary=True,
    )


@pytest.fixture
def test_fact() -> Fact:
    """Test fact for integration testing."""
    return Fact(
        name="Paris",
        type="Location",
    )


@pytest.fixture
def test_source() -> Source:
    """Test source for integration testing."""
    return Source(
        content="User mentioned they live in Paris during onboarding",
        timestamp=datetime.now(),
    )


class TestCreateEntity:
    """Integration tests for ArcadedbRepository.create_entity method."""

    @pytest.mark.asyncio
    async def test_create_entity_basic(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test basic entity creation with minimal data."""

        # Act
        result: CreateEntityResult = await arcadedb_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
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
        assert (
            returned_relationship.is_primary
            == test_has_identifier_relationship.is_primary
        )

    @pytest.mark.asyncio
    async def test_create_entity_reuses_existing_identifier(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test that create_entity reuses existing identifiers instead of creating duplicates.

        This tests the idempotent behavior for identifiers: when creating entities with
        identifiers that have the same value and type, the existing identifier should
        be reused rather than creating a new duplicate identifier.
        """

        # First, create an entity with the test identifier
        first_entity = test_entity
        first_relationship = test_has_identifier_relationship

        first_result = await arcadedb_repository.create_entity(
            first_entity, test_identifier, first_relationship
        )

        # Verify first entity was created
        assert first_result is not None
        assert first_result["entity"].id == first_entity.id

        # Create a second entity with the SAME identifier (same value and type)
        second_entity = Entity(
            metadata={
                "test_type": "reuse_identifier_test",
                "test_run_id": str(uuid.uuid4()),
                "created_by": "test_entity_reuse_identifier.py",
            }
        )
        second_relationship = HasIdentifier(
            from_entity_id=second_entity.id,
            to_identifier_value=test_identifier.value,  # Same identifier value
            is_primary=True,
        )

        # Act - Create second entity with same identifier
        second_result = await arcadedb_repository.create_entity(
            second_entity, test_identifier, second_relationship
        )

        # Assert
        assert second_result is not None
        assert second_result["entity"].id == second_entity.id

        # Both entities should exist and be findable
        first_found = await arcadedb_repository.find_entity_by_id(str(first_entity.id))
        second_found = await arcadedb_repository.find_entity_by_id(
            str(second_entity.id)
        )

        assert first_found is not None
        assert second_found is not None

        # Both should have the same primary identifier
        first_identifier = first_found["identifier"]["identifier"]
        second_identifier = second_found["identifier"]["identifier"]

        # The identifiers should be identical (same value and type)
        assert first_identifier.value == test_identifier.value
        assert first_identifier.type == test_identifier.type
        assert second_identifier.value == test_identifier.value
        assert second_identifier.type == test_identifier.type

        # Verify we can find both entities by the same identifier
        # (Note: find_entity_by_identifier might return either entity since both are connected)
        found_by_identifier = await arcadedb_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert found_by_identifier is not None
        # It should find one of the entities (which one depends on database ordering)


class TestFindEntityByIdentifier:
    """Integration tests for GraphRepository.find_entity_by_identifier method."""

    @pytest.mark.asyncio
    async def test_find_entity_by_identifier(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test finding an entity by its identifier value and type."""

        # First create the entity with identifier
        _ = await arcadedb_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )

        # Act - Find the entity by identifier
        find_result = await arcadedb_repository.find_entity_by_identifier(
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
        assert (
            found_relationship.is_primary == test_has_identifier_relationship.is_primary
        )
        assert found_relationship.from_entity_id == test_entity.id
        assert found_relationship.to_identifier_value == test_identifier.value


class TestFindEntityById:
    """Integration tests for GraphRepository.find_entity_by_id method."""

    @pytest.mark.asyncio
    async def test_find_entity_by_id(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test finding an entity by its ID."""

        # First create the entity with identifier
        _ = await arcadedb_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )

        # Act - Find the entity by its ID
        find_result = await arcadedb_repository.find_entity_by_id(str(test_entity.id))

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
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
    ) -> None:
        """Test finding an entity by its ID when it has no identifiers."""

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
        find_result = await arcadedb_repository.find_entity_by_id(str(test_entity.id))
        print("DEBUG - Find result: ", find_result)

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
        arcadedb_repository: ArcadedbRepository,
    ) -> None:
        """Test finding an entity by ID when it doesn't exist."""
        # Act - Try to find a non-existent entity
        find_result = await arcadedb_repository.find_entity_by_id("non-existent-id")

        # Assert
        assert find_result is None

    @pytest.mark.asyncio
    async def test_find_entity_by_id_empty_id(
        self,
        arcadedb_repository: ArcadedbRepository,
    ) -> None:
        """Test finding an entity with empty ID raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Entity ID cannot be empty"):
            _ = await arcadedb_repository.find_entity_by_id("")


class TestDeleteEntityById:
    """Integration tests for GraphRepository.delete_entity_by_id method."""

    @pytest.mark.asyncio
    async def test_delete_entity_by_id(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test deleting an entity by its ID."""

        # First create the entity with identifier
        _ = await arcadedb_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )

        # Verify the entity exists by finding it
        found_before = await arcadedb_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert found_before is not None

        # Act - Delete the entity by its ID
        delete_result = await arcadedb_repository.delete_entity_by_id(
            str(test_entity.id)
        )

        # Assert
        assert delete_result is True

        # Verify the entity was actually deleted
        found_after = await arcadedb_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert found_after is None  # Should not find the entity anymore

    @pytest.mark.asyncio
    async def test_delete_entity_by_id_not_found(
        self,
        arcadedb_repository: ArcadedbRepository,
    ) -> None:
        """Test deleting an entity that doesn't exist."""
        # Act - Try to delete a non-existent entity
        delete_result = await arcadedb_repository.delete_entity_by_id("non-existent-id")

        # Assert
        assert delete_result is False

    @pytest.mark.asyncio
    async def test_delete_entity_with_shared_identifier(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test that identifiers shared by multiple entities are not deleted."""

        # Create first entity with identifier
        _ = await arcadedb_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )

        # Create second entity with the same identifier
        second_entity = Entity(metadata={"test_type": "shared_identifier_test"})
        second_relationship = HasIdentifier(
            from_entity_id=second_entity.id,
            to_identifier_value=test_identifier.value,
            is_primary=True,
        )
        _ = await arcadedb_repository.create_entity(
            second_entity, test_identifier, second_relationship
        )

        # Delete the first entity
        delete_result = await arcadedb_repository.delete_entity_by_id(
            str(test_entity.id)
        )
        assert delete_result is True

        # Verify first entity is gone
        found_first = await arcadedb_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert found_first is not None  # Should still find the second entity

        # Clean up second entity
        _ = await arcadedb_repository.delete_entity_by_id(str(second_entity.id))

    # @TODO: verify this test
    @pytest.mark.asyncio
    async def test_delete_entity_cascading_cleanup_orphaned_identifiers(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
    ) -> None:
        """Test that delete_entity_by_id removes orphaned identifiers but preserves shared ones.

        This test creates two scenarios:
        1. An entity with a unique identifier (orphaned when entity is deleted)
        2. Two entities sharing the same identifier (preserved when one entity is deleted)

        Setup:
        - entity_with_unique: has unique_identifier (only connected to entity_with_unique)
        - entity_with_unique: also has shared_identifier (connected to both entities)
        - entity_with_shared: has shared_identifier (connected to both entities)

        When entity_with_unique is deleted:
        - unique_identifier should be deleted (orphaned)
        - shared_identifier should be preserved (still connected to entity_with_shared)
        """

        # Create identifiers
        unique_identifier = Identifier(
            value=f"unique.test.{uuid.uuid4()}@example.com", type="email"
        )
        shared_identifier = Identifier(
            value=f"shared.test.{uuid.uuid4()}@example.com", type="email"
        )

        # Create Entity A (will be deleted) - the entity with both unique and shared identifiers
        entity_with_unique = test_entity
        unique_relationship = HasIdentifier(
            from_entity_id=entity_with_unique.id,
            to_identifier_value=unique_identifier.value,
            is_primary=False,  # Not primary since we'll have a shared one
        )
        shared_relationship_a = HasIdentifier(
            from_entity_id=entity_with_unique.id,
            to_identifier_value=shared_identifier.value,
            is_primary=True,  # Primary identifier
        )

        # Create Entity A with unique identifier first
        _ = await arcadedb_repository.create_entity(
            entity_with_unique, unique_identifier, unique_relationship
        )

        # Add shared identifier to Entity A (this creates a second HAS_IDENTIFIER edge)
        # We need to manually create this since create_entity only handles one identifier
        database_name = get_database_name()
        db = await get_graph_db()
        add_shared_to_entity_a_query = f"""
        CREATE EDGE HAS_IDENTIFIER
        FROM (SELECT FROM Entity WHERE id = '{entity_with_unique.id}')
        TO (SELECT FROM Identifier WHERE value = '{shared_identifier.value}' AND type = '{shared_identifier.type}')
        UPSERT WHERE value = '{shared_identifier.value}' AND type = '{shared_identifier.type}'
        SET is_primary = {str(shared_relationship_a.is_primary).lower()},
            created_at = '{shared_relationship_a.created_at.isoformat()}'
        """
        await db.execute_command(
            add_shared_to_entity_a_query, database_name, language="sql"
        )

        # Create Entity B with the shared identifier (the one that will survive)
        entity_with_shared = Entity(
            metadata={"test_type": "entity_with_shared_identifier_cleanup_test"}
        )
        shared_relationship_b = HasIdentifier(
            from_entity_id=entity_with_shared.id,
            to_identifier_value=shared_identifier.value,
            is_primary=True,
        )

        # Create Entity B with shared identifier
        _ = await arcadedb_repository.create_entity(
            entity_with_shared, shared_identifier, shared_relationship_b
        )

        # Verify both entities exist and can be found
        entity_a_found = await arcadedb_repository.find_entity_by_identifier(
            unique_identifier.value, unique_identifier.type
        )
        assert entity_a_found is not None
        assert entity_a_found["entity"].id == entity_with_unique.id

        entity_b_found = await arcadedb_repository.find_entity_by_identifier(
            shared_identifier.value, shared_identifier.type
        )
        assert (
            entity_b_found is not None
        )  # Should find one of the entities with shared identifier

        # Act - Delete Entity A (should cascade to unique identifier but preserve shared one)
        delete_result = await arcadedb_repository.delete_entity_by_id(
            str(entity_with_unique.id)
        )

        # Assert deletion was successful
        assert delete_result is True

        # Verify Entity A is completely gone
        entity_a_after = await arcadedb_repository.find_entity_by_id(
            str(entity_with_unique.id)
        )
        assert entity_a_after is None

        # Verify unique identifier is gone (orphaned and should have been cleaned up)
        unique_identifier_after = await arcadedb_repository.find_entity_by_identifier(
            unique_identifier.value, unique_identifier.type
        )
        assert unique_identifier_after is None

        # Verify shared identifier still exists (still connected to Entity B)
        shared_identifier_after = await arcadedb_repository.find_entity_by_identifier(
            shared_identifier.value, shared_identifier.type
        )
        assert shared_identifier_after is not None
        assert shared_identifier_after["entity"].id == entity_with_shared.id

        # Clean up - delete Entity B
        cleanup_result = await arcadedb_repository.delete_entity_by_id(
            str(entity_with_shared.id)
        )
        assert cleanup_result is True


class TestAddFactToEntity:
    """Integration tests for ArcadedbRepository.add_fact_to_entity method."""

    @pytest.mark.asyncio
    async def test_add_fact_to_entity_basic(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
        test_fact: Fact,
        test_source: Source,
    ) -> None:
        """Test basic fact addition to an entity."""

        # First create the entity
        create_result = await arcadedb_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )
        assert create_result is not None

        # Act - Add fact to entity
        result: AddFactToEntityResult = await arcadedb_repository.add_fact_to_entity(
            entity_id=str(test_entity.id),
            fact=test_fact,
            source=test_source,
            verb="lives_in",
            confidence_score=0.9,
        )

        # Assert
        assert isinstance(result, dict)
        assert "fact" in result
        assert "source" in result
        assert "has_fact_relationship" in result
        assert "derived_from_relationship" in result

        # Verify returned objects have correct properties
        returned_fact = result["fact"]
        returned_source = result["source"]
        returned_has_fact = result["has_fact_relationship"]
        returned_derived_from = result["derived_from_relationship"]

        assert isinstance(returned_fact, Fact)
        assert isinstance(returned_source, Source)
        assert isinstance(returned_has_fact, HasFact)
        assert isinstance(returned_derived_from, DerivedFrom)

        # Check fact properties
        assert returned_fact.name == test_fact.name
        assert returned_fact.type == test_fact.type
        assert returned_fact.fact_id == test_fact.fact_id

        # Check source properties
        assert returned_source.id == test_source.id
        assert returned_source.content == test_source.content

        # Check has_fact relationship
        assert returned_has_fact.from_entity_id == test_entity.id
        assert returned_has_fact.to_fact_id == test_fact.fact_id
        assert returned_has_fact.verb == "lives_in"
        assert returned_has_fact.confidence_score == 0.9

        # Check derived_from relationship
        assert returned_derived_from.from_fact_id == test_fact.fact_id
        assert returned_derived_from.to_source_id == test_source.id

    @pytest.mark.asyncio
    async def test_add_fact_to_entity_with_facts_retrieved(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
        test_fact: Fact,
        test_source: Source,
    ) -> None:
        """Test that added facts can be retrieved when finding the entity."""

        # First create the entity
        create_result = await arcadedb_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )
        assert create_result is not None

        # Add fact to entity
        add_result = await arcadedb_repository.add_fact_to_entity(
            entity_id=str(test_entity.id),
            fact=test_fact,
            source=test_source,
            verb="lives_in",
        )
        assert add_result is not None

        # Find entity by ID to verify facts are retrievable
        found_entity = await arcadedb_repository.find_entity_by_id(str(test_entity.id))
        assert found_entity is not None

        # Verify the fact was added
        facts_with_sources = found_entity["facts_with_sources"]
        assert len(facts_with_sources) == 1

        fact_with_source = facts_with_sources[0]
        assert fact_with_source["fact"].name == test_fact.name
        assert fact_with_source["fact"].type == test_fact.type
        assert fact_with_source["source"] is not None
        assert fact_with_source["source"].content == test_source.content
        assert fact_with_source["relationship"].verb == "lives_in"

    @pytest.mark.asyncio
    async def test_add_fact_to_entity_invalid_entity_id(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_fact: Fact,
        test_source: Source,
    ) -> None:
        """Test adding fact to non-existent entity raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Entity ID cannot be empty"):
            _ = await arcadedb_repository.add_fact_to_entity(
                entity_id="",
                fact=test_fact,
                source=test_source,
                verb="lives_in",
            )

    @pytest.mark.asyncio
    async def test_add_fact_to_entity_invalid_fact(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_source: Source,
    ) -> None:
        """Test adding invalid fact raises ValueError."""
        # Create fact without fact_id
        invalid_fact = Fact(name="Test", type="Test")
        invalid_fact.fact_id = None  # Manually set to None to test validation

        # Act & Assert
        with pytest.raises(ValueError, match="Fact must have a valid fact_id"):
            _ = await arcadedb_repository.add_fact_to_entity(
                entity_id=str(test_entity.id),
                fact=invalid_fact,
                source=test_source,
                verb="lives_in",
            )

    @pytest.mark.asyncio
    async def test_add_fact_to_entity_invalid_verb(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_fact: Fact,
        test_source: Source,
    ) -> None:
        """Test adding fact with empty verb raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Verb cannot be empty"):
            _ = await arcadedb_repository.add_fact_to_entity(
                entity_id=str(test_entity.id),
                fact=test_fact,
                source=test_source,
                verb="",
            )

    @pytest.mark.asyncio
    async def test_add_fact_to_entity_invalid_confidence_score(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_fact: Fact,
        test_source: Source,
    ) -> None:
        """Test adding fact with invalid confidence score raises ValueError."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="Confidence score must be between 0.0 and 1.0"
        ):
            _ = await arcadedb_repository.add_fact_to_entity(
                entity_id=str(test_entity.id),
                fact=test_fact,
                source=test_source,
                verb="lives_in",
                confidence_score=1.5,  # Invalid: greater than 1.0
            )

        with pytest.raises(
            ValueError, match="Confidence score must be between 0.0 and 1.0"
        ):
            _ = await arcadedb_repository.add_fact_to_entity(
                entity_id=str(test_entity.id),
                fact=test_fact,
                source=test_source,
                verb="lives_in",
                confidence_score=-0.1,  # Invalid: less than 0.0
            )

    @pytest.mark.asyncio
    async def test_add_fact_to_entity_multiple_facts(
        self,
        arcadedb_repository: ArcadedbRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test adding multiple facts to the same entity."""

        # First create the entity
        create_result = await arcadedb_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )
        assert create_result is not None

        # Create multiple facts with sources
        facts_data: list[_TestFactItem] = [
            {
                "fact": Fact(name="Paris", type="Location"),
                "source": Source(content="User profile", timestamp=datetime.now()),
                "verb": "lives_in",
            },
            {
                "fact": Fact(name="Engineer", type="Occupation"),
                "source": Source(content="Job application", timestamp=datetime.now()),
                "verb": "works_as",
            },
            {
                "fact": Fact(name="Soccer", type="Interest"),
                "source": Source(content="Survey response", timestamp=datetime.now()),
                "verb": "interested_in",
            },
        ]

        # Add each fact to the entity
        for fact_item in facts_data:
            result = await arcadedb_repository.add_fact_to_entity(
                entity_id=str(test_entity.id),
                fact=fact_item["fact"],
                source=fact_item["source"],
                verb=fact_item["verb"],
            )
            assert result is not None

        # Verify all facts were added
        found_entity = await arcadedb_repository.find_entity_by_id(str(test_entity.id))
        assert found_entity is not None

        facts_with_sources = found_entity["facts_with_sources"]
        assert len(facts_with_sources) == 3

        # Check that all facts are present
        fact_names = {fws["fact"].name for fws in facts_with_sources}
        expected_names = {"Paris", "Engineer", "Soccer"}
        assert fact_names == expected_names
