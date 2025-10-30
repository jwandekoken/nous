"""Integration tests for AgeRepository using a real PostgreSQL/AGE connection."""

import uuid
from datetime import datetime

import asyncpg
import pytest

from app.features.graph.models import Entity, Fact, HasIdentifier, Identifier, Source
from app.features.graph.repositories.age_repository import AgeRepository


@pytest.fixture
async def age_repository(postgres_pool: asyncpg.Pool) -> AgeRepository:
    """Fixture to get an AgeRepository instance."""
    return AgeRepository(postgres_pool, graph_name="test_graph")


@pytest.fixture
def test_entity() -> Entity:
    """Test entity with integration test metadata."""
    return Entity(
        metadata={
            "test_type": "integration",
            "test_run_id": str(uuid.uuid4()),
            "created_by": "test_age_repository_integration.py",
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
    """Integration tests for AgeRepository.create_entity method."""

    @pytest.mark.asyncio
    async def test_create_entity_basic(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test basic entity creation with minimal data."""
        # Act
        result = await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )

        # Assert
        assert isinstance(result, dict)
        assert "entity" in result
        assert "identifier" in result
        assert "relationship" in result

        returned_entity = result["entity"]
        returned_identifier = result["identifier"]
        returned_relationship = result["relationship"]

        assert isinstance(returned_entity, Entity)
        assert isinstance(returned_identifier, Identifier)
        assert isinstance(returned_relationship, HasIdentifier)

        assert returned_entity.id == test_entity.id
        assert returned_entity.metadata == test_entity.metadata
        assert returned_identifier.value == test_identifier.value
        assert returned_identifier.type == test_identifier.type
        assert (
            returned_relationship.is_primary
            == test_has_identifier_relationship.is_primary
        )

        # Verify by finding it
        found = await age_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert found is not None
        assert found["entity"].id == test_entity.id

    @pytest.mark.asyncio
    async def test_create_entity_is_idempotent(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test that create_entity is idempotent."""
        # Create it once
        first_result = await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )
        assert first_result["entity"].id == test_entity.id

        # Try to create it again with a different entity object but same identifier
        second_entity = Entity()
        second_relationship = HasIdentifier(
            from_entity_id=second_entity.id,
            to_identifier_value=test_identifier.value,
        )
        second_result = await age_repository.create_entity(
            second_entity, test_identifier, second_relationship
        )

        # Assert it returned the first entity
        assert second_result["entity"].id == first_result["entity"].id
        assert second_result["entity"].id == test_entity.id


class TestFindEntityByIdentifier:
    """Integration tests for AgeRepository.find_entity_by_identifier method."""

    @pytest.mark.asyncio
    async def test_find_entity_by_identifier(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test finding an entity by its identifier value and type."""
        # Arrange: Create an entity first
        await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )

        # Act
        found_result = await age_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )

        # Assert
        assert found_result is not None
        found_entity = found_result["entity"]
        found_identifier = found_result["identifier"]["identifier"]
        found_rel = found_result["identifier"]["relationship"]

        assert found_entity.id == test_entity.id
        assert found_identifier.value == test_identifier.value
        assert found_rel.from_entity_id == test_entity.id

    @pytest.mark.asyncio
    async def test_find_entity_by_identifier_not_found(
        self,
        age_repository: AgeRepository,
    ) -> None:
        """Test finding a non-existent entity."""
        found_result = await age_repository.find_entity_by_identifier(
            "nonexistent@example.com", "email"
        )
        assert found_result is None


class TestFindEntityById:
    """Integration tests for AgeRepository.find_entity_by_id method."""

    @pytest.mark.asyncio
    async def test_find_entity_by_id(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test finding an entity by its ID."""
        # Arrange
        await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )

        # Act
        found_result = await age_repository.find_entity_by_id(str(test_entity.id))

        # Assert
        assert found_result is not None
        assert found_result["entity"].id == test_entity.id
        assert found_result["identifier"] is not None
        assert found_result["identifier"]["identifier"].value == test_identifier.value

    @pytest.mark.asyncio
    async def test_find_entity_by_id_not_found(
        self,
        age_repository: AgeRepository,
    ) -> None:
        """Test finding a non-existent entity by ID."""
        found_result = await age_repository.find_entity_by_id(str(uuid.uuid4()))
        assert found_result is None


class TestDeleteEntityById:
    """Integration tests for AgeRepository.delete_entity_by_id method."""

    @pytest.mark.asyncio
    async def test_delete_entity_by_id(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test deleting an entity by its ID."""
        # Arrange
        _ = await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )
        # Act
        delete_result = await age_repository.delete_entity_by_id(str(test_entity.id))

        # Assert
        assert delete_result is True
        found_after = await age_repository.find_entity_by_id(str(test_entity.id))
        assert found_after is None

    @pytest.mark.asyncio
    async def test_delete_entity_by_id_not_found(
        self,
        age_repository: AgeRepository,
    ) -> None:
        """Test deleting a non-existent entity."""
        delete_result = await age_repository.delete_entity_by_id(str(uuid.uuid4()))
        assert delete_result is False

    @pytest.mark.asyncio
    async def test_delete_entity_cascades_to_unique_identifier(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test that deleting an entity also deletes its unique identifier."""
        # Arrange: Create entity with identifier
        _ = await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )

        # Verify identifier exists
        found_before = await age_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert found_before is not None

        # Act: Delete the entity
        delete_result = await age_repository.delete_entity_by_id(str(test_entity.id))
        assert delete_result is True

        # Assert: Identifier should also be deleted since it was only used by this entity
        found_after = await age_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert found_after is None

    @pytest.mark.asyncio
    async def test_delete_entity_does_not_affect_other_entities(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
    ) -> None:
        """Test that deleting one entity doesn't affect other entities with different identifiers."""
        # Arrange: Create first entity
        _ = await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )

        # Create second entity with different identifier
        second_entity = Entity()
        second_identifier = Identifier(
            value=f"second.{uuid.uuid4()}@example.com", type="email"
        )
        second_relationship = HasIdentifier(
            from_entity_id=second_entity.id,
            to_identifier_value=second_identifier.value,
        )
        _ = await age_repository.create_entity(
            second_entity, second_identifier, second_relationship
        )

        # Act: Delete the first entity
        delete_result = await age_repository.delete_entity_by_id(str(test_entity.id))
        assert delete_result is True

        # Assert: Second entity should still exist
        found_second = await age_repository.find_entity_by_identifier(
            second_identifier.value, second_identifier.type
        )
        assert found_second is not None
        assert found_second["entity"].id == second_entity.id

        # And first entity should be gone
        found_first = await age_repository.find_entity_by_identifier(
            test_identifier.value, test_identifier.type
        )
        assert found_first is None

    @pytest.mark.asyncio
    async def test_delete_entity_cascades_to_unique_facts(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
        test_fact: Fact,
        test_source: Source,
    ) -> None:
        """Test that deleting an entity also deletes its unique facts and sources."""
        # Arrange: Create entity with fact and source
        _ = await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )
        _ = await age_repository.add_fact_to_entity(
            entity_id=str(test_entity.id),
            fact=test_fact,
            source=test_source,
            verb="lives_in",
        )

        # Verify fact exists
        assert test_fact.fact_id is not None
        fact_before = await age_repository.find_fact_by_id(test_fact.fact_id)
        assert fact_before is not None

        # Act: Delete the entity
        delete_result = await age_repository.delete_entity_by_id(str(test_entity.id))
        assert delete_result is True

        # Assert: Fact should also be deleted since it was only used by this entity
        fact_after = await age_repository.find_fact_by_id(test_fact.fact_id)
        assert fact_after is None

    @pytest.mark.asyncio
    async def test_delete_entity_preserves_shared_facts(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
        test_fact: Fact,
        test_source: Source,
    ) -> None:
        """Test that deleting an entity preserves facts shared with other entities."""
        # Arrange: Create first entity with fact
        _ = await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )
        _ = await age_repository.add_fact_to_entity(
            entity_id=str(test_entity.id),
            fact=test_fact,
            source=test_source,
            verb="lives_in",
        )

        # Create second entity and add the same fact to it
        second_entity = Entity()
        second_identifier = Identifier(
            value=f"second.{uuid.uuid4()}@example.com", type="email"
        )
        second_relationship = HasIdentifier(
            from_entity_id=second_entity.id,
            to_identifier_value=second_identifier.value,
        )
        _ = await age_repository.create_entity(
            second_entity, second_identifier, second_relationship
        )
        _ = await age_repository.add_fact_to_entity(
            entity_id=str(second_entity.id),
            fact=test_fact,  # Same fact
            source=test_source,  # Same source
            verb="works_in",  # Different verb
        )

        # Act: Delete the first entity
        delete_result = await age_repository.delete_entity_by_id(str(test_entity.id))
        assert delete_result is True

        # Assert: Fact should still exist because it's used by the second entity
        assert test_fact.fact_id is not None
        fact_after = await age_repository.find_fact_by_id(test_fact.fact_id)
        assert fact_after is not None

        # And the second entity should still have the fact
        second_entity_found = await age_repository.find_entity_by_id(
            str(second_entity.id)
        )
        assert second_entity_found is not None
        assert len(second_entity_found["facts_with_sources"]) == 1
        assert (
            second_entity_found["facts_with_sources"][0]["fact"].fact_id
            == test_fact.fact_id
        )


class TestAddFactToEntity:
    """Integration tests for AgeRepository.add_fact_to_entity method."""

    @pytest.mark.asyncio
    async def test_add_fact_to_entity_basic(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
        test_fact: Fact,
        test_source: Source,
    ) -> None:
        """Test basic fact addition to an entity."""
        # Arrange
        _ = await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )

        # Act
        result = await age_repository.add_fact_to_entity(
            entity_id=str(test_entity.id),
            fact=test_fact,
            source=test_source,
            verb="lives_in",
            confidence_score=0.9,
        )

        # Assert
        assert result["fact"].name == test_fact.name
        assert result["source"].content == test_source.content
        assert result["has_fact_relationship"].verb == "lives_in"
        assert result["has_fact_relationship"].confidence_score == 0.9

        # Verify
        found = await age_repository.find_entity_by_id(str(test_entity.id))
        assert found is not None
        assert len(found["facts_with_sources"]) == 1
        assert found["facts_with_sources"][0]["fact"].name == test_fact.name

    @pytest.mark.asyncio
    async def test_add_fact_to_entity_is_idempotent(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
        test_fact: Fact,
        test_source: Source,
    ) -> None:
        """Test that adding the same fact is idempotent."""
        # Arrange
        _ = await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )
        # Act
        _ = await age_repository.add_fact_to_entity(
            entity_id=str(test_entity.id),
            fact=test_fact,
            source=test_source,
            verb="lives_in",
        )
        _ = await age_repository.add_fact_to_entity(
            entity_id=str(test_entity.id),
            fact=test_fact,
            source=test_source,
            verb="lives_in",
        )
        # Assert
        found = await age_repository.find_entity_by_id(str(test_entity.id))
        assert found is not None
        assert len(found["facts_with_sources"]) == 1


class TestFindFactById:
    """Integration tests for AgeRepository.find_fact_by_id method."""

    @pytest.mark.asyncio
    async def test_find_fact_by_id(
        self,
        age_repository: AgeRepository,
        test_entity: Entity,
        test_identifier: Identifier,
        test_has_identifier_relationship: HasIdentifier,
        test_fact: Fact,
        test_source: Source,
    ) -> None:
        """Test finding a fact by its fact_id."""
        # Arrange
        await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )
        await age_repository.add_fact_to_entity(
            entity_id=str(test_entity.id),
            fact=test_fact,
            source=test_source,
            verb="lives_in",
        )

        # Act
        assert test_fact.fact_id is not None
        found = await age_repository.find_fact_by_id(test_fact.fact_id)

        # Assert
        assert found is not None
        assert found["fact"].fact_id == test_fact.fact_id
        assert found["source"] is not None
        assert found["source"].id == test_source.id

    @pytest.mark.asyncio
    async def test_find_fact_by_id_not_found(
        self,
        age_repository: AgeRepository,
    ) -> None:
        """Test finding a non-existent fact."""
        found = await age_repository.find_fact_by_id("non:existent")
        assert found is None
