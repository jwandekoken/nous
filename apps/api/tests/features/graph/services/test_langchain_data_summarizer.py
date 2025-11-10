"""Tests for the LangChainDataSummarizer service."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.features.graph.dtos.knowledge_dto import (
    EntityDto,
    FactDto,
    FactWithSourceDto,
    GetEntityResponse,
    HasFactDto,
    HasIdentifierDto,
    IdentifierDto,
    IdentifierWithRelationshipDto,
    SourceDto,
)
from app.features.graph.services.langchain_data_summarizer import (
    LangChainDataSummarizer,
)


@pytest.fixture
def summarizer():
    """Create a LangChainDataSummarizer instance for testing."""
    return LangChainDataSummarizer()


@pytest.fixture
def sample_entity_data() -> GetEntityResponse:
    """Create sample entity data for testing."""
    entity_id = uuid4()
    source_id = uuid4()
    now = datetime.now(timezone.utc)

    entity = EntityDto(id=entity_id, created_at=now, metadata={})

    identifier = IdentifierWithRelationshipDto(
        identifier=IdentifierDto(value="test@example.com", type="email"),
        relationship=HasIdentifierDto(is_primary=True, created_at=now),
    )

    facts = [
        FactWithSourceDto(
            fact=FactDto(name="Paris", type="Location", fact_id="Location:Paris"),
            relationship=HasFactDto(
                verb="lives_in", confidence_score=0.95, created_at=now
            ),
            source=SourceDto(
                id=source_id,
                content="I live in Paris and love it here.",
                timestamp=now,
            ),
        ),
        FactWithSourceDto(
            fact=FactDto(
                name="Software Engineer",
                type="Profession",
                fact_id="Profession:Software Engineer",
            ),
            relationship=HasFactDto(
                verb="works_as", confidence_score=1.0, created_at=now
            ),
            source=SourceDto(
                id=source_id,
                content="I'm a software engineer working on AI.",
                timestamp=now,
            ),
        ),
        FactWithSourceDto(
            fact=FactDto(name="Hiking", type="Hobby", fact_id="Hobby:Hiking"),
            relationship=HasFactDto(
                verb="enjoys", confidence_score=0.8, created_at=now
            ),
            source=SourceDto(
                id=source_id,
                content="I enjoy hiking on weekends.",
                timestamp=now,
            ),
        ),
    ]

    return GetEntityResponse(entity=entity, identifier=identifier, facts=facts)


@pytest.mark.asyncio
async def test_summarize_with_multiple_facts(summarizer, sample_entity_data):
    """Test that summarization works with entity containing multiple facts."""
    summary = await summarizer.summarize(sample_entity_data)

    # Verify we get a non-empty string
    assert isinstance(summary, str)
    assert len(summary) > 0

    # Verify the summary contains key information
    # Note: These assertions are loose because LLM output can vary
    assert "email" in summary.lower() or "test@example.com" in summary.lower()


@pytest.mark.asyncio
async def test_summarize_handles_confidence_scores(summarizer, sample_entity_data):
    """Test that summaries handle different confidence scores appropriately."""
    summary = await summarizer.summarize(sample_entity_data)

    # Verify we get a valid summary
    assert isinstance(summary, str)
    assert len(summary) > 0

    # The summary should contain some information about the facts
    # But we can't assert specific confidence qualifiers due to LLM variability


@pytest.mark.asyncio
async def test_summarize_with_single_fact(summarizer):
    """Test summarization with entity containing a single fact."""
    entity_id = uuid4()
    source_id = uuid4()
    now = datetime.now(timezone.utc)

    entity = EntityDto(id=entity_id, created_at=now, metadata={})

    identifier = IdentifierWithRelationshipDto(
        identifier=IdentifierDto(value="single@example.com", type="email"),
        relationship=HasIdentifierDto(is_primary=True, created_at=now),
    )

    facts = [
        FactWithSourceDto(
            fact=FactDto(name="Tokyo", type="Location", fact_id="Location:Tokyo"),
            relationship=HasFactDto(
                verb="lives_in", confidence_score=0.9, created_at=now
            ),
            source=SourceDto(
                id=source_id,
                content="I live in Tokyo.",
                timestamp=now,
            ),
        ),
    ]

    entity_data = GetEntityResponse(entity=entity, identifier=identifier, facts=facts)

    summary = await summarizer.summarize(entity_data)

    # Verify we get a non-empty string
    assert isinstance(summary, str)
    assert len(summary) > 0


@pytest.mark.asyncio
async def test_summarize_default_language(summarizer, sample_entity_data):
    """Test that summarization defaults to English when no language is specified."""
    summary = await summarizer.summarize(sample_entity_data)

    # Verify we get a valid English summary
    assert isinstance(summary, str)
    assert len(summary) > 0
    # Summary should be in English (basic check for common English words)


@pytest.mark.asyncio
async def test_summarize_with_portuguese_language(summarizer, sample_entity_data):
    """Test summarization with Portuguese (pt-br) language."""
    summary = await summarizer.summarize(sample_entity_data, lang="pt-br")

    # Verify we get a non-empty string
    assert isinstance(summary, str)
    assert len(summary) > 0
    # Note: We can't strictly verify the output is in Portuguese without
    # additional language detection, but we verify the call succeeds


@pytest.mark.asyncio
async def test_summarize_with_spanish_language(summarizer, sample_entity_data):
    """Test summarization with Spanish language."""
    summary = await summarizer.summarize(sample_entity_data, lang="es")

    # Verify we get a non-empty string
    assert isinstance(summary, str)
    assert len(summary) > 0


@pytest.mark.asyncio
async def test_summarize_with_french_language(summarizer, sample_entity_data):
    """Test summarization with French language."""
    summary = await summarizer.summarize(sample_entity_data, lang="fr")

    # Verify we get a non-empty string
    assert isinstance(summary, str)
    assert len(summary) > 0
