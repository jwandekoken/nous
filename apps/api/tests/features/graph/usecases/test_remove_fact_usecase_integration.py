"""Integration tests for RemoveFactFromEntityUseCaseImpl using real dependencies.

This module provides integration tests for the RemoveFactFromEntityUseCaseImpl
using the actual production implementation of AgeRepository.
"""

import uuid

import asyncpg
import pytest
from fastapi import HTTPException

from app.features.graph.dtos.knowledge_dto import RemoveFactFromEntityResponse
from app.features.graph.models import Entity, Fact, HasIdentifier, Identifier, Source
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.usecases.remove_fact_usecase import (
    RemoveFactFromEntityUseCaseImpl,
)


@pytest.fixture
async def age_repository(postgres_pool: asyncpg.Pool) -> AgeRepository:
    """Fixture to get an AgeRepository instance."""
    return AgeRepository(postgres_pool, graph_name="test_graph")


@pytest.fixture
async def remove_fact_usecase(
    age_repository: AgeRepository,
) -> RemoveFactFromEntityUseCaseImpl:
    """RemoveFactFromEntityUseCaseImpl instance for testing."""
    return RemoveFactFromEntityUseCaseImpl(repository=age_repository)


class TestRemoveFactFromEntityUseCaseIntegration:
    """Integration tests for RemoveFactFromEntityUseCaseImpl.execute method."""

    @pytest.mark.asyncio
    async def test_remove_fact_from_entity_success(
        self,
        remove_fact_usecase: RemoveFactFromEntityUseCaseImpl,
        age_repository: AgeRepository,
    ) -> None:
        """Test successful removal of a fact from an entity."""
        # Arrange: Create entity with fact
        entity = Entity()
        identifier = Identifier(value=f"test.{uuid.uuid4()}@example.com", type="email")
        relationship = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=identifier.value,
            is_primary=True,
        )
        _ = await age_repository.create_entity(entity, identifier, relationship)

        fact = Fact(name="Paris", type="Location")
        source = Source(content="User mentioned they live in Paris")
        _ = await age_repository.add_fact_to_entity(
            entity_id=str(entity.id),
            fact=fact,
            source=source,
            verb="lives_in",
        )

        # Act: Remove the fact
        assert fact.fact_id is not None
        result: RemoveFactFromEntityResponse = await remove_fact_usecase.execute(
            entity_id=entity.id, fact_id=fact.fact_id
        )

        # Assert
        assert isinstance(result, RemoveFactFromEntityResponse)
        assert result.success is True
        assert result.entity_id == entity.id
        assert result.fact_id == fact.fact_id
        assert "successfully removed" in result.message.lower()

        # Verify fact was actually removed from database
        entity_after = await age_repository.find_entity_by_id(str(entity.id))
        assert entity_after is not None
        assert len(entity_after["facts_with_sources"]) == 0

    @pytest.mark.asyncio
    async def test_remove_fact_not_found_raises_404(
        self,
        remove_fact_usecase: RemoveFactFromEntityUseCaseImpl,
        age_repository: AgeRepository,
    ) -> None:
        """Test that removing a non-existent fact raises HTTPException with 404."""
        # Arrange: Create entity without any facts
        entity = Entity()
        identifier = Identifier(value=f"test.{uuid.uuid4()}@example.com", type="email")
        relationship = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=identifier.value,
            is_primary=True,
        )
        _ = await age_repository.create_entity(entity, identifier, relationship)

        # Act & Assert: Try to remove non-existent fact
        with pytest.raises(HTTPException) as exc_info:
            await remove_fact_usecase.execute(
                entity_id=entity.id, fact_id="Location:NonExistent"
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_remove_fact_preserves_other_facts(
        self,
        remove_fact_usecase: RemoveFactFromEntityUseCaseImpl,
        age_repository: AgeRepository,
    ) -> None:
        """Test that removing one fact doesn't affect other facts on the same entity."""
        # Arrange: Create entity with two facts
        entity = Entity()
        identifier = Identifier(value=f"test.{uuid.uuid4()}@example.com", type="email")
        relationship = HasIdentifier(
            from_entity_id=entity.id,
            to_identifier_value=identifier.value,
            is_primary=True,
        )
        _ = await age_repository.create_entity(entity, identifier, relationship)

        fact1 = Fact(name="Paris", type="Location")
        source1 = Source(content="Lives in Paris")
        _ = await age_repository.add_fact_to_entity(
            entity_id=str(entity.id),
            fact=fact1,
            source=source1,
            verb="lives_in",
        )

        fact2 = Fact(name="Python", type="Skill")
        source2 = Source(content="Knows Python")
        _ = await age_repository.add_fact_to_entity(
            entity_id=str(entity.id),
            fact=fact2,
            source=source2,
            verb="has_skill",
        )

        # Act: Remove only the first fact
        assert fact1.fact_id is not None
        result = await remove_fact_usecase.execute(
            entity_id=entity.id, fact_id=fact1.fact_id
        )

        # Assert
        assert result.success is True

        # Verify only fact1 was removed, fact2 remains
        entity_after = await age_repository.find_entity_by_id(str(entity.id))
        assert entity_after is not None
        assert len(entity_after["facts_with_sources"]) == 1
        assert entity_after["facts_with_sources"][0]["fact"].fact_id == fact2.fact_id

    @pytest.mark.asyncio
    async def test_remove_shared_fact_from_one_entity(
        self,
        remove_fact_usecase: RemoveFactFromEntityUseCaseImpl,
        age_repository: AgeRepository,
    ) -> None:
        """Test removing a fact from one entity when the fact is shared with another entity."""
        # Arrange: Create two entities with the same fact
        entity1 = Entity()
        identifier1 = Identifier(
            value=f"test1.{uuid.uuid4()}@example.com", type="email"
        )
        relationship1 = HasIdentifier(
            from_entity_id=entity1.id,
            to_identifier_value=identifier1.value,
            is_primary=True,
        )
        _ = await age_repository.create_entity(entity1, identifier1, relationship1)

        entity2 = Entity()
        identifier2 = Identifier(
            value=f"test2.{uuid.uuid4()}@example.com", type="email"
        )
        relationship2 = HasIdentifier(
            from_entity_id=entity2.id,
            to_identifier_value=identifier2.value,
            is_primary=True,
        )
        _ = await age_repository.create_entity(entity2, identifier2, relationship2)

        # Add the same fact to both entities
        shared_fact = Fact(name="Paris", type="Location")
        source = Source(content="Both live in Paris")
        _ = await age_repository.add_fact_to_entity(
            entity_id=str(entity1.id),
            fact=shared_fact,
            source=source,
            verb="lives_in",
        )
        _ = await age_repository.add_fact_to_entity(
            entity_id=str(entity2.id),
            fact=shared_fact,
            source=source,
            verb="lives_in",
        )

        # Act: Remove the fact from entity1 only
        assert shared_fact.fact_id is not None
        result = await remove_fact_usecase.execute(
            entity_id=entity1.id, fact_id=shared_fact.fact_id
        )

        # Assert
        assert result.success is True

        # Verify fact was removed from entity1
        entity1_after = await age_repository.find_entity_by_id(str(entity1.id))
        assert entity1_after is not None
        assert len(entity1_after["facts_with_sources"]) == 0

        # Verify fact still exists for entity2
        entity2_after = await age_repository.find_entity_by_id(str(entity2.id))
        assert entity2_after is not None
        assert len(entity2_after["facts_with_sources"]) == 1
        assert (
            entity2_after["facts_with_sources"][0]["fact"].fact_id
            == shared_fact.fact_id
        )

        # Verify the fact itself still exists in the database
        fact_still_exists = await age_repository.find_fact_by_id(shared_fact.fact_id)
        assert fact_still_exists is not None
