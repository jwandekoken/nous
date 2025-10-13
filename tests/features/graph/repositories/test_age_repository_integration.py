"""Integration tests for AgeRepository using a real PostgreSQL/AGE connection."""

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import cast

import asyncpg
import pytest

from app.core.settings import get_settings
from app.db.postgres.connection import close_db_pool, get_db_pool
from app.features.graph.models import Entity, Fact, HasIdentifier, Identifier, Source
from app.features.graph.repositories.age_repository import AgeRepository


@pytest.fixture
async def postgres_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Provides a connection pool and ensures it's closed after the test."""
    pool = await get_db_pool()
    try:
        yield pool
    finally:
        await close_db_pool()


@pytest.fixture
async def age_repository(postgres_pool: asyncpg.Pool) -> AgeRepository:
    """Fixture to get an AgeRepository instance."""
    return AgeRepository(postgres_pool)


@pytest.fixture(autouse=True)
async def clean_graph_db(postgres_pool: asyncpg.Pool) -> None:
    """Clean all data from the AGE graph before each test."""
    settings = get_settings()
    graph_name = settings.age_graph_name

    async with postgres_pool.acquire() as conn:
        conn = cast(asyncpg.Connection, conn)
        async with conn.transaction():
            await conn.execute("LOAD 'age';")
            await conn.execute("SET search_path = ag_catalog, '$user', public;")
            # The VACUUM command is used to reclaim storage occupied by dead tuples. In this case, it is used to clean the graph.
            await conn.execute(
                f"SELECT * from ag_catalog.cypher('{graph_name}', $$ MATCH (n) DETACH DELETE n $$) as (v agtype);"
            )


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
        await age_repository.create_entity(
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
        await age_repository.create_entity(
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
        await age_repository.create_entity(
            test_entity, test_identifier, test_has_identifier_relationship
        )
        # Act
        await age_repository.add_fact_to_entity(
            entity_id=str(test_entity.id),
            fact=test_fact,
            source=test_source,
            verb="lives_in",
        )
        await age_repository.add_fact_to_entity(
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
