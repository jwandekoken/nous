"""Tests for the GetEntitySummaryUseCase."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.features.graph.dtos.knowledge_dto import (
    EntityDto,
    FactDto,
    FactWithSourceDto,
    GetEntityResponse,
    GetEntitySummaryResponse,
    HasFactDto,
    HasIdentifierDto,
    IdentifierDto,
    IdentifierWithRelationshipDto,
    SourceDto,
)
from app.features.graph.services.langchain_data_summarizer import (
    LangChainDataSummarizer,
)
from app.features.graph.usecases.get_entity_summary import GetEntitySummaryUseCaseImpl
from app.features.graph.usecases.get_entity_usecase import GetEntityUseCaseImpl


@pytest.fixture
def mock_get_entity_use_case():
    """Create a mock GetEntityUseCaseImpl."""
    return AsyncMock(spec=GetEntityUseCaseImpl)


@pytest.fixture
def mock_data_summarizer():
    """Create a mock LangChainDataSummarizer."""
    return AsyncMock(spec=LangChainDataSummarizer)


@pytest.fixture
def use_case(mock_get_entity_use_case, mock_data_summarizer):
    """Create a GetEntitySummaryUseCaseImpl with mocked dependencies."""
    return GetEntitySummaryUseCaseImpl(
        get_entity_use_case=mock_get_entity_use_case,
        data_summarizer=mock_data_summarizer,
    )


@pytest.fixture
def sample_entity_with_facts() -> GetEntityResponse:
    """Create sample entity data with facts."""
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
                content="I live in Paris.",
                timestamp=now,
            ),
        ),
    ]

    return GetEntityResponse(entity=entity, identifier=identifier, facts=facts)


@pytest.fixture
def sample_entity_without_facts() -> GetEntityResponse:
    """Create sample entity data without facts."""
    entity_id = uuid4()
    now = datetime.now(timezone.utc)

    entity = EntityDto(id=entity_id, created_at=now, metadata={})

    identifier = IdentifierWithRelationshipDto(
        identifier=IdentifierDto(value="empty@example.com", type="email"),
        relationship=HasIdentifierDto(is_primary=True, created_at=now),
    )

    return GetEntityResponse(entity=entity, identifier=identifier, facts=[])


@pytest.mark.asyncio
async def test_execute_with_facts(
    use_case, mock_get_entity_use_case, mock_data_summarizer, sample_entity_with_facts
):
    """Test successful summary generation with facts."""
    # Setup mocks
    mock_get_entity_use_case.execute.return_value = sample_entity_with_facts
    expected_summary = "This entity lives in Paris with high confidence."
    mock_data_summarizer.summarize.return_value = expected_summary

    # Execute
    result = await use_case.execute(
        identifier_value="test@example.com", identifier_type="email"
    )

    # Verify
    assert isinstance(result, GetEntitySummaryResponse)
    assert result.summary == expected_summary
    assert result.entity == sample_entity_with_facts.entity
    assert result.identifier == sample_entity_with_facts.identifier

    # Verify mocks were called correctly
    mock_get_entity_use_case.execute.assert_called_once_with(
        identifier_value="test@example.com", identifier_type="email"
    )
    mock_data_summarizer.summarize.assert_called_once_with(sample_entity_with_facts)


@pytest.mark.asyncio
async def test_execute_without_facts_skips_llm(
    use_case,
    mock_get_entity_use_case,
    mock_data_summarizer,
    sample_entity_without_facts,
):
    """Test that entity with no facts skips LLM call and returns static message."""
    # Setup mocks
    mock_get_entity_use_case.execute.return_value = sample_entity_without_facts

    # Execute
    result = await use_case.execute(
        identifier_value="empty@example.com", identifier_type="email"
    )

    # Verify
    assert isinstance(result, GetEntitySummaryResponse)
    assert result.summary == "This entity has no recorded facts in the knowledge graph."
    assert result.entity == sample_entity_without_facts.entity
    assert result.identifier == sample_entity_without_facts.identifier

    # Verify LLM was NOT called (cost optimization)
    mock_data_summarizer.summarize.assert_not_called()

    # Verify get_entity was still called
    mock_get_entity_use_case.execute.assert_called_once_with(
        identifier_value="empty@example.com", identifier_type="email"
    )


@pytest.mark.asyncio
async def test_execute_entity_not_found_propagates_exception(
    use_case, mock_get_entity_use_case, mock_data_summarizer
):
    """Test that entity not found exception is properly propagated."""
    # Setup mock to raise HTTPException
    mock_get_entity_use_case.execute.side_effect = HTTPException(
        status_code=404,
        detail="Entity with identifier 'email:notfound@example.com' not found",
    )

    # Execute and verify exception is raised
    with pytest.raises(HTTPException) as exc_info:
        await use_case.execute(
            identifier_value="notfound@example.com", identifier_type="email"
        )

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()

    # Verify LLM was NOT called
    mock_data_summarizer.summarize.assert_not_called()


@pytest.mark.asyncio
async def test_execute_passes_correct_parameters(
    use_case, mock_get_entity_use_case, mock_data_summarizer, sample_entity_with_facts
):
    """Test that execute passes correct parameters to dependencies."""
    # Setup mocks
    mock_get_entity_use_case.execute.return_value = sample_entity_with_facts
    mock_data_summarizer.summarize.return_value = "Summary text"

    # Execute with specific parameters
    await use_case.execute(identifier_value="user@test.com", identifier_type="email")

    # Verify correct parameters were passed
    mock_get_entity_use_case.execute.assert_called_once_with(
        identifier_value="user@test.com", identifier_type="email"
    )
