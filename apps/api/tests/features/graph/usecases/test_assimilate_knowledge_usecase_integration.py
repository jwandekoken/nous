"""Integration tests for AssimilateKnowledgeUseCaseImpl using real dependencies.

This module provides integration tests for the AssimilateKnowledgeUseCaseImpl
using the actual production implementations of AgeRepository and LangChainFactExtractor.
"""

import uuid

import asyncpg
import pytest

from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    AssimilateKnowledgeResponse,
    IdentifierDto,
)
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.services.langchain_fact_extractor import LangChainFactExtractor
from app.features.graph.usecases.assimilate_knowledge_usecase import (
    AssimilateKnowledgeUseCaseImpl,
)


@pytest.fixture
async def age_repository(postgres_pool: asyncpg.Pool) -> AgeRepository:
    """Fixture to get an AgeRepository instance."""
    return AgeRepository(postgres_pool, graph_name="test_graph")


@pytest.fixture
def langchain_fact_extractor() -> LangChainFactExtractor:
    """LangChainFactExtractor instance for testing."""
    return LangChainFactExtractor()


@pytest.fixture
async def assimilate_knowledge_usecase(
    age_repository: AgeRepository,
    langchain_fact_extractor: LangChainFactExtractor,
) -> AssimilateKnowledgeUseCaseImpl:
    """AssimilateKnowledgeUseCaseImpl instance for testing."""
    return AssimilateKnowledgeUseCaseImpl(
        repository=age_repository, fact_extractor=langchain_fact_extractor
    )


@pytest.fixture
def test_identifier() -> IdentifierDto:
    """Test identifier payload for integration testing."""
    return IdentifierDto(
        value=f"test.integration.{uuid.uuid4()}@example.com", type="email"
    )


@pytest.fixture
def test_content() -> str:
    """Test content for fact extraction."""
    return "I live in Paris and work as a Software Engineer. I really enjoy hiking on weekends."


class TestAssimilateKnowledgeUseCaseIntegration:
    """Integration tests for AssimilateKnowledgeUseCaseImpl.execute method."""

    @pytest.mark.asyncio
    async def test_assimilate_knowledge_basic(
        self,
        assimilate_knowledge_usecase: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
        test_content: str,
    ) -> None:
        """Test basic knowledge assimilation flow with fact extraction."""

        # Act
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content=test_content,
        )

        result: AssimilateKnowledgeResponse = (
            await assimilate_knowledge_usecase.execute(request)
        )
        print(f"{result=}")

        # Assert
        assert isinstance(result, AssimilateKnowledgeResponse)
        assert result.entity is not None
        assert result.source is not None
        assert result.assimilated_facts is not None

        # Verify entity was created with correct ID
        assert result.entity.id is not None
        assert isinstance(result.entity.metadata, dict)

        # Verify source was created correctly
        assert result.source.id is not None
        assert result.source.content == test_content
        assert result.source.timestamp is not None  # Should be auto-generated

        # Verify facts were extracted and assimilated
        # The exact facts depend on the LLM output, but we expect some facts
        assert len(result.assimilated_facts) > 0

        # Check structure of assimilated facts
        for assimilated_fact in result.assimilated_facts:
            assert assimilated_fact.fact is not None
            assert assimilated_fact.fact.name is not None
            assert assimilated_fact.fact.type is not None
            assert assimilated_fact.fact.fact_id is not None
            assert assimilated_fact.relationship is not None
            assert assimilated_fact.relationship.verb is not None
            assert 0.0 <= assimilated_fact.relationship.confidence_score <= 1.0
            assert assimilated_fact.relationship.created_at is not None

    @pytest.mark.asyncio
    async def test_assimilate_knowledge_creates_new_entity(
        self,
        assimilate_knowledge_usecase: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
        test_content: str,
    ) -> None:
        """Test that assimilate knowledge creates a new entity when identifier doesn't exist."""

        # Act
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content=test_content,
        )

        result = await assimilate_knowledge_usecase.execute(request)

        # Assert
        assert result.entity is not None
        assert result.entity.id is not None

        # Verify the entity can be found in the database
        found_entity = (
            await assimilate_knowledge_usecase.repository.find_entity_by_identifier(
                test_identifier.value, test_identifier.type
            )
        )
        assert found_entity is not None
        assert found_entity["entity"].id == result.entity.id

    @pytest.mark.asyncio
    async def test_assimilate_knowledge_reuses_existing_entity(
        self,
        assimilate_knowledge_usecase: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
        test_content: str,
    ) -> None:
        """Test that assimilate knowledge reuses existing entity when identifier already exists."""

        # First, create an entity with the identifier
        first_request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content="Initial content about the entity.",
        )

        first_result = await assimilate_knowledge_usecase.execute(first_request)
        first_entity_id = first_result.entity.id

        # Now assimilate more knowledge with the same identifier
        second_request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content=test_content,
        )

        second_result = await assimilate_knowledge_usecase.execute(second_request)

        # Assert that the same entity was reused
        assert second_result.entity.id == first_entity_id

        # Verify both sets of facts are associated with the same entity
        found_entity = await assimilate_knowledge_usecase.repository.find_entity_by_id(
            str(first_entity_id)
        )
        assert found_entity is not None

        # Should have facts from both assimilation calls
        facts_with_sources = found_entity["facts_with_sources"]
        assert len(facts_with_sources) > 0

    @pytest.mark.asyncio
    async def test_assimilate_knowledge_with_history(
        self,
        assimilate_knowledge_usecase: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test knowledge assimilation with conversation history for context."""

        history = [
            "Hello, I'm John and I'm 25 years old.",
            "I moved to Paris last year.",
        ]

        current_content = "I work as a software engineer now."

        # Act
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content=current_content,
            history=history,
        )

        result = await assimilate_knowledge_usecase.execute(request)

        # Assert
        assert result.entity is not None
        assert result.source is not None
        assert len(result.assimilated_facts) > 0

        # The fact extractor should use the history for better context
        # We can't predict exact facts, but ensure the process completes successfully

    @pytest.mark.asyncio
    async def test_assimilate_knowledge_no_facts_extracted(
        self,
        assimilate_knowledge_usecase: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test knowledge assimilation when no facts can be extracted from content."""

        # Content that should not yield any facts
        content = (
            "This is just a generic message with no specific information about me."
        )

        # Act
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content=content,
        )

        result = await assimilate_knowledge_usecase.execute(request)

        # Assert
        assert result.entity is not None
        assert result.source is not None
        # The fact extractor might still extract some facts, or it might return empty
        # We just verify the process completes without error
        assert isinstance(result.assimilated_facts, list)

    @pytest.mark.asyncio
    async def test_assimilate_knowledge_multiple_facts(
        self,
        assimilate_knowledge_usecase: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test assimilation of content that should yield multiple facts."""

        # Content designed to yield multiple distinct facts about the entity
        content = """I live in San Francisco, California.
        I work as a Senior Product Manager at a tech company. I graduated from Stanford University
        with a degree in Computer Science. I speak English, Spanish, and French fluently.
        My hobbies include photography, hiking, and playing the piano."""

        # Act
        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content=content,
        )

        result = await assimilate_knowledge_usecase.execute(request)
        print(f"---> result: {result}")

        # Assert
        assert result.entity is not None
        assert result.source is not None

        # Should extract multiple facts
        assert len(result.assimilated_facts) > 1

        # Verify all facts have proper structure
        fact_types: set[str] = set()
        for assimilated_fact in result.assimilated_facts:
            assert assimilated_fact.fact.name
            assert assimilated_fact.fact.type
            assert assimilated_fact.fact.fact_id
            assert assimilated_fact.relationship.verb
            assert 0.0 <= assimilated_fact.relationship.confidence_score <= 1.0
            fact_types.add(assimilated_fact.fact.type)

        # Should have variety in fact types
        assert len(fact_types) > 1

    @pytest.mark.asyncio
    async def test_assimilate_knowledge_different_languages(
        self,
        assimilate_knowledge_usecase: AssimilateKnowledgeUseCaseImpl,
        test_identifier: IdentifierDto,
    ) -> None:
        """Test knowledge assimilation with content in different languages."""

        # Test with Spanish content
        spanish_content = "Me llamo María García. Vivo en Barcelona y trabajo como profesora de matemáticas."

        request = AssimilateKnowledgeRequest(
            identifier=test_identifier,
            content=spanish_content,
        )

        result = await assimilate_knowledge_usecase.execute(request)
        print(f"---> result: {result}")

        # Assert
        assert result.entity is not None
        assert result.source is not None
        assert len(result.assimilated_facts) > 0

        # Fact names should be in original language, types and verbs in English
        for assimilated_fact in result.assimilated_facts:
            assert assimilated_fact.fact.name  # Could be in Spanish
            assert assimilated_fact.fact.type  # Should be in English
            assert assimilated_fact.relationship.verb  # Should be in English
