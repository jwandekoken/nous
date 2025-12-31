"""Integration tests for QdrantRepository using a real Qdrant connection.

This module provides comprehensive tests for the QdrantRepository class,
covering:
- Add semantic operations (including idempotency)
- Search semantic operations (including relevance and filtering)
- Delete semantic operations
- Tenant isolation and entity scoping
"""

import uuid

import pytest
from qdrant_client import AsyncQdrantClient

from app.features.graph.models import Fact
from app.features.graph.repositories.protocols import SemanticSearchResult
from app.features.graph.repositories.qdrant_repository import QdrantRepository
from app.features.graph.services.embedding_service import EmbeddingService
from tests.conftest import TEST_QDRANT_COLLECTION


@pytest.fixture
def qdrant_repository(
    qdrant_client: AsyncQdrantClient,
    embedding_service: EmbeddingService,
) -> QdrantRepository:
    """Fixture to get a QdrantRepository instance for testing."""
    return QdrantRepository(
        client=qdrant_client,
        embedding_service=embedding_service,
        tenant_id="test_tenant",
        collection_name=TEST_QDRANT_COLLECTION,
    )


@pytest.fixture
def test_fact() -> Fact:
    """Test fact for vector operations."""
    return Fact(name="Paris", type="Location")


@pytest.fixture
def test_fact_hobby() -> Fact:
    """Test hobby fact for vector operations."""
    return Fact(name="Hiking", type="Hobby")


@pytest.fixture
def test_fact_profession() -> Fact:
    """Test profession fact for vector operations."""
    return Fact(name="Software Engineering", type="Profession")


class TestVectorRepositoryAddSemantic:
    """Integration tests for VectorRepository.add_semantic_memory method."""

    @pytest.mark.asyncio
    async def test_add_semantic_memory_basic(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
    ) -> None:
        """Test basic semantic vector addition."""
        entity_id = uuid.uuid4()

        # Act
        result = await qdrant_repository.add_semantic_memory(
            entity_id=entity_id,
            fact=test_fact,
            verb="lives_in",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_add_semantic_memory_creates_searchable_vector(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
    ) -> None:
        """Test that adding a semantic vector makes it searchable."""
        entity_id = uuid.uuid4()

        # Add the semantic vector
        await qdrant_repository.add_semantic_memory(
            entity_id=entity_id,
            fact=test_fact,
            verb="lives_in",
        )

        # Search for it
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="Where does this person live?",
            top_k=10,
        )

        # Assert
        assert len(results) == 1
        assert results[0].fact_id == test_fact.fact_id
        assert results[0].verb == "lives_in"

    @pytest.mark.asyncio
    async def test_add_semantic_memory_is_idempotent(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
    ) -> None:
        """Test that adding the same semantic vector is idempotent."""
        entity_id = uuid.uuid4()

        # Add twice
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")

        # Assert: Should have only one point (due to deterministic ID)
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="location",
            top_k=10,
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_add_semantic_memory_different_verbs_creates_separate_vectors(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
    ) -> None:
        """Test that the same fact with different verbs creates separate vectors."""
        entity_id = uuid.uuid4()

        # Add same fact with different verbs
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "works_in")

        # Assert: Should have two vectors
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="Paris",
            top_k=10,
        )
        assert len(results) == 2
        verbs = {r.verb for r in results}
        assert verbs == {"lives_in", "works_in"}

    @pytest.mark.asyncio
    async def test_add_semantic_memory_stores_correct_payload(
        self,
        qdrant_repository: QdrantRepository,
        qdrant_client: AsyncQdrantClient,
        test_fact: Fact,
    ) -> None:
        """Test that add_semantic_memory stores the correct payload metadata."""
        entity_id = uuid.uuid4()

        # Add the semantic vector
        await qdrant_repository.add_semantic_memory(
            entity_id=entity_id,
            fact=test_fact,
            verb="lives_in",
        )

        # Directly query Qdrant to check payload
        response = await qdrant_client.scroll(
            collection_name=TEST_QDRANT_COLLECTION,
            limit=10,
            with_payload=True,
        )

        # Assert
        assert len(response[0]) == 1
        point = response[0][0]
        payload = point.payload

        assert payload is not None
        assert payload["tenant_id"] == "test_tenant"
        assert payload["entity_id"] == str(entity_id)
        assert payload["fact_id"] == test_fact.fact_id
        assert payload["verb"] == "lives_in"
        assert payload["type"] == "semantic"
        assert payload["fact_name"] == "Paris"
        assert payload["fact_type"] == "Location"
        assert (
            f"{entity_id}:lives_in:{test_fact.fact_id}" in payload["relationship_key"]
        )

    @pytest.mark.asyncio
    async def test_add_semantic_memory_raises_on_missing_fact_id(
        self,
        qdrant_repository: QdrantRepository,
    ) -> None:
        """Test that add_semantic_memory raises ValueError if fact has no fact_id."""
        entity_id = uuid.uuid4()
        # Create a fact without triggering the model validator
        # This is a bit tricky since Pydantic auto-generates fact_id
        # We'll test the error path by mocking
        fact = Fact(name="Test", type="Test")
        # Forcefully set fact_id to None (simulating edge case)
        object.__setattr__(fact, "fact_id", None)

        with pytest.raises(ValueError, match="Fact must have a fact_id"):
            await qdrant_repository.add_semantic_memory(
                entity_id=entity_id,
                fact=fact,
                verb="test",
            )


class TestVectorRepositorySearchSemantic:
    """Integration tests for VectorRepository.search_semantic_memory method."""

    @pytest.mark.asyncio
    async def test_search_semantic_memory_finds_relevant_fact(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
        test_fact_hobby: Fact,
        test_fact_profession: Fact,
    ) -> None:
        """Test that semantic search finds relevant facts."""
        entity_id = uuid.uuid4()

        # Add multiple facts
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")
        await qdrant_repository.add_semantic_memory(
            entity_id, test_fact_hobby, "enjoys"
        )
        await qdrant_repository.add_semantic_memory(
            entity_id, test_fact_profession, "works_as"
        )

        # Search for location-related query
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="Where does this person live?",
            top_k=3,
        )

        # The top result should be the location fact
        assert len(results) > 0
        assert results[0].fact_id == "Location:Paris"

    @pytest.mark.asyncio
    async def test_search_semantic_memory_finds_hobby_fact(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
        test_fact_hobby: Fact,
        test_fact_profession: Fact,
    ) -> None:
        """Test that semantic search finds hobby-related facts."""
        entity_id = uuid.uuid4()

        # Add multiple facts
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")
        await qdrant_repository.add_semantic_memory(
            entity_id, test_fact_hobby, "enjoys"
        )
        await qdrant_repository.add_semantic_memory(
            entity_id, test_fact_profession, "works_as"
        )

        # Search for hobby-related query
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="What are their hobbies and outdoor activities?",
            top_k=3,
        )

        # The top result should be the hobby fact
        assert len(results) > 0
        assert results[0].fact_id == "Hobby:Hiking"

    @pytest.mark.asyncio
    async def test_search_semantic_memory_returns_empty_for_no_matches(
        self,
        qdrant_repository: QdrantRepository,
    ) -> None:
        """Test that search returns empty list when no facts exist."""
        entity_id = uuid.uuid4()

        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="Where does this person live?",
            top_k=10,
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_semantic_memory_respects_top_k(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
        test_fact_hobby: Fact,
        test_fact_profession: Fact,
    ) -> None:
        """Test that search respects the top_k limit."""
        entity_id = uuid.uuid4()

        # Add multiple facts
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")
        await qdrant_repository.add_semantic_memory(
            entity_id, test_fact_hobby, "enjoys"
        )
        await qdrant_repository.add_semantic_memory(
            entity_id, test_fact_profession, "works_as"
        )

        # Search with top_k=2
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="Tell me about this person",
            top_k=2,
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_semantic_memory_respects_min_score(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
        test_fact_hobby: Fact,
    ) -> None:
        """Test that search respects the min_score threshold."""
        entity_id = uuid.uuid4()

        # Add facts
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")
        await qdrant_repository.add_semantic_memory(
            entity_id, test_fact_hobby, "enjoys"
        )

        # Search with very high min_score (should return nothing)
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="Where does this person live?",
            top_k=10,
            min_score=0.99,  # Very high threshold
        )

        # Should return no results (or very few) due to high threshold
        # Note: The exact behavior depends on how similar the query is
        # We're testing that the parameter is respected
        assert len(results) <= 1

    @pytest.mark.asyncio
    async def test_search_semantic_memory_returns_correct_result_type(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
    ) -> None:
        """Test that search returns SemanticSearchResult objects."""
        entity_id = uuid.uuid4()

        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")

        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="location",
            top_k=10,
        )

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, SemanticSearchResult)
        assert result.fact_id == "Location:Paris"
        assert result.verb == "lives_in"
        assert f"{entity_id}:lives_in:Location:Paris" == result.relationship_key
        assert isinstance(result.score, float)
        assert 0.0 <= result.score <= 1.0

    @pytest.mark.asyncio
    async def test_search_semantic_memory_results_ordered_by_score(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
        test_fact_hobby: Fact,
        test_fact_profession: Fact,
    ) -> None:
        """Test that search results are ordered by score (descending)."""
        entity_id = uuid.uuid4()

        # Add multiple facts
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")
        await qdrant_repository.add_semantic_memory(
            entity_id, test_fact_hobby, "enjoys"
        )
        await qdrant_repository.add_semantic_memory(
            entity_id, test_fact_profession, "works_as"
        )

        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="general query",
            top_k=10,
        )

        # Verify results are ordered by score (descending)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score


class TestVectorRepositoryDeleteSemantic:
    """Integration tests for VectorRepository.delete_semantic_memory method."""

    @pytest.mark.asyncio
    async def test_delete_semantic_memory_removes_vector(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
    ) -> None:
        """Test that deleting a semantic vector removes it from the collection."""
        entity_id = uuid.uuid4()

        # Add then delete
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")

        assert test_fact.fact_id is not None
        await qdrant_repository.delete_semantic_memory(
            entity_id=entity_id,
            fact_id=test_fact.fact_id,
            verb="lives_in",
        )

        # Search should return nothing
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="location",
            top_k=10,
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_semantic_memory_only_removes_specified_verb(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
    ) -> None:
        """Test that delete only removes the vector with the specified verb."""
        entity_id = uuid.uuid4()

        # Add same fact with different verbs
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "works_in")

        # Delete only one verb
        assert test_fact.fact_id is not None
        await qdrant_repository.delete_semantic_memory(
            entity_id=entity_id,
            fact_id=test_fact.fact_id,
            verb="lives_in",
        )

        # Should still find the other verb
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="Paris",
            top_k=10,
        )
        assert len(results) == 1
        assert results[0].verb == "works_in"

    @pytest.mark.asyncio
    async def test_delete_semantic_memory_returns_true(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
    ) -> None:
        """Test that delete_semantic_memory returns True on success."""
        entity_id = uuid.uuid4()

        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")

        assert test_fact.fact_id is not None
        result = await qdrant_repository.delete_semantic_memory(
            entity_id=entity_id,
            fact_id=test_fact.fact_id,
            verb="lives_in",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_semantic_memory_on_nonexistent_returns_true(
        self,
        qdrant_repository: QdrantRepository,
    ) -> None:
        """Test that deleting a non-existent vector still returns True (Qdrant behavior)."""
        entity_id = uuid.uuid4()

        # Delete something that doesn't exist
        result = await qdrant_repository.delete_semantic_memory(
            entity_id=entity_id,
            fact_id="NonExistent:Fact",
            verb="nonexistent",
        )

        # Qdrant delete is idempotent - returns success even if point didn't exist
        assert result is True


class TestVectorRepositoryDeleteAllForEntity:
    """Integration tests for VectorRepository.delete_all_semantic_memories_for_entity method."""

    @pytest.mark.asyncio
    async def test_delete_all_semantic_memories_for_entity_removes_all_vectors(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
        test_fact_hobby: Fact,
        test_fact_profession: Fact,
    ) -> None:
        """Test that delete_all_semantic_memories_for_entity removes all vectors for an entity."""
        entity_id = uuid.uuid4()

        # Add multiple facts
        await qdrant_repository.add_semantic_memory(entity_id, test_fact, "lives_in")
        await qdrant_repository.add_semantic_memory(
            entity_id, test_fact_hobby, "enjoys"
        )
        await qdrant_repository.add_semantic_memory(
            entity_id, test_fact_profession, "works_as"
        )

        # Delete all
        count = await qdrant_repository.delete_all_semantic_memories_for_entity(
            entity_id
        )

        # Assert count
        assert count == 3

        # Search should return nothing
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="anything",
            top_k=10,
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_all_semantic_memories_for_entity_does_not_affect_other_entities(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
    ) -> None:
        """Test that delete_all_semantic_memories_for_entity only affects the specified entity."""
        entity_id_1 = uuid.uuid4()
        entity_id_2 = uuid.uuid4()

        # Add facts for both entities
        await qdrant_repository.add_semantic_memory(entity_id_1, test_fact, "lives_in")
        await qdrant_repository.add_semantic_memory(entity_id_2, test_fact, "lives_in")

        # Delete all for entity 1
        await qdrant_repository.delete_all_semantic_memories_for_entity(entity_id_1)

        # Entity 2's facts should still exist
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id_2,
            query_text="location",
            top_k=10,
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_delete_all_semantic_memories_for_entity_returns_zero_when_none_exist(
        self,
        qdrant_repository: QdrantRepository,
    ) -> None:
        """Test that delete_all_semantic_memories_for_entity returns 0 when no vectors exist."""
        entity_id = uuid.uuid4()

        count = await qdrant_repository.delete_all_semantic_memories_for_entity(
            entity_id
        )

        assert count == 0


class TestVectorRepositoryTenantIsolation:
    """Integration tests for VectorRepository tenant isolation."""

    @pytest.mark.asyncio
    async def test_search_semantic_memory_respects_tenant_isolation(
        self,
        qdrant_client: AsyncQdrantClient,
        embedding_service: EmbeddingService,
        test_fact: Fact,
    ) -> None:
        """Test that search only returns results for the current tenant."""
        entity_id = uuid.uuid4()

        # Create repos for two different tenants
        repo_tenant_a = QdrantRepository(
            client=qdrant_client,
            embedding_service=embedding_service,
            tenant_id="tenant_a",
            collection_name=TEST_QDRANT_COLLECTION,
        )
        repo_tenant_b = QdrantRepository(
            client=qdrant_client,
            embedding_service=embedding_service,
            tenant_id="tenant_b",
            collection_name=TEST_QDRANT_COLLECTION,
        )

        # Add fact from tenant A
        await repo_tenant_a.add_semantic_memory(entity_id, test_fact, "lives_in")

        # Search from tenant B - should NOT find tenant A's data
        results = await repo_tenant_b.search_semantic_memory(
            entity_id=entity_id,
            query_text="location",
            top_k=10,
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_different_tenants_can_have_same_entity_id(
        self,
        qdrant_client: AsyncQdrantClient,
        embedding_service: EmbeddingService,
        test_fact: Fact,
        test_fact_hobby: Fact,
    ) -> None:
        """Test that different tenants can use the same entity_id without conflict."""
        # Same entity_id for both tenants
        entity_id = uuid.uuid4()

        repo_tenant_a = QdrantRepository(
            client=qdrant_client,
            embedding_service=embedding_service,
            tenant_id="tenant_a",
            collection_name=TEST_QDRANT_COLLECTION,
        )
        repo_tenant_b = QdrantRepository(
            client=qdrant_client,
            embedding_service=embedding_service,
            tenant_id="tenant_b",
            collection_name=TEST_QDRANT_COLLECTION,
        )

        # Add different facts for same entity_id but different tenants
        await repo_tenant_a.add_semantic_memory(entity_id, test_fact, "lives_in")
        await repo_tenant_b.add_semantic_memory(entity_id, test_fact_hobby, "enjoys")

        # Each tenant should only see their own data
        results_a = await repo_tenant_a.search_semantic_memory(
            entity_id=entity_id,
            query_text="any",
            top_k=10,
        )
        results_b = await repo_tenant_b.search_semantic_memory(
            entity_id=entity_id,
            query_text="any",
            top_k=10,
        )

        assert len(results_a) == 1
        assert results_a[0].fact_id == "Location:Paris"

        assert len(results_b) == 1
        assert results_b[0].fact_id == "Hobby:Hiking"

    @pytest.mark.asyncio
    async def test_delete_respects_tenant_isolation(
        self,
        qdrant_client: AsyncQdrantClient,
        embedding_service: EmbeddingService,
        test_fact: Fact,
    ) -> None:
        """Test that delete operations respect tenant isolation."""
        entity_id = uuid.uuid4()

        repo_tenant_a = QdrantRepository(
            client=qdrant_client,
            embedding_service=embedding_service,
            tenant_id="tenant_a",
            collection_name=TEST_QDRANT_COLLECTION,
        )
        repo_tenant_b = QdrantRepository(
            client=qdrant_client,
            embedding_service=embedding_service,
            tenant_id="tenant_b",
            collection_name=TEST_QDRANT_COLLECTION,
        )

        # Add fact for both tenants
        await repo_tenant_a.add_semantic_memory(entity_id, test_fact, "lives_in")
        await repo_tenant_b.add_semantic_memory(entity_id, test_fact, "lives_in")

        # Delete from tenant A
        await repo_tenant_a.delete_all_semantic_memories_for_entity(entity_id)

        # Tenant B's data should still exist
        results_b = await repo_tenant_b.search_semantic_memory(
            entity_id=entity_id,
            query_text="location",
            top_k=10,
        )
        assert len(results_b) == 1


class TestVectorRepositoryEntityScoping:
    """Integration tests for VectorRepository entity scoping."""

    @pytest.mark.asyncio
    async def test_search_scoped_to_entity(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
        test_fact_hobby: Fact,
    ) -> None:
        """Test that search is scoped to the specified entity."""
        entity_id_1 = uuid.uuid4()
        entity_id_2 = uuid.uuid4()

        # Add location to entity 1, hobby to entity 2
        await qdrant_repository.add_semantic_memory(entity_id_1, test_fact, "lives_in")
        await qdrant_repository.add_semantic_memory(
            entity_id_2, test_fact_hobby, "enjoys"
        )

        # Search entity 1 for location
        results_1 = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id_1,
            query_text="location",
            top_k=10,
        )

        # Should only find entity 1's fact
        assert len(results_1) == 1
        assert results_1[0].fact_id == "Location:Paris"

        # Search entity 2 for hobby
        results_2 = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id_2,
            query_text="hobby",
            top_k=10,
        )

        # Should only find entity 2's fact
        assert len(results_2) == 1
        assert results_2[0].fact_id == "Hobby:Hiking"

    @pytest.mark.asyncio
    async def test_search_does_not_cross_entity_boundaries(
        self,
        qdrant_repository: QdrantRepository,
        test_fact: Fact,
    ) -> None:
        """Test that searching one entity doesn't return another entity's facts."""
        entity_id_1 = uuid.uuid4()
        entity_id_2 = uuid.uuid4()

        # Add fact only to entity 1
        await qdrant_repository.add_semantic_memory(entity_id_1, test_fact, "lives_in")

        # Search entity 2 - should find nothing even with matching query
        results = await qdrant_repository.search_semantic_memory(
            entity_id=entity_id_2,
            query_text="Where does this person live?",
            top_k=10,
        )

        assert len(results) == 0
