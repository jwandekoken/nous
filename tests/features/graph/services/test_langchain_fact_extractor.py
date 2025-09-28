"""Integration tests for the LangChainFactExtractor service.

These tests actually call the Gemini LLM API, so they require:
- GOOGLE_API_KEY environment variable to be set
- Internet connection for API calls
"""

from unittest.mock import patch

import pytest

from app.features.graph.dtos.knowledge_dto import ExtractedFactDto, IdentifierPayload
from app.features.graph.services.langchain_fact_extractor import LangChainFactExtractor


class TestLangChainFactExtractor:
    """Test suite for LangChainFactExtractor integration with Gemini API."""

    @pytest.fixture
    def extractor(self) -> LangChainFactExtractor:
        """Create a LangChainFactExtractor instance for testing."""
        return LangChainFactExtractor()

    def test_initialization_without_api_key(self):
        """Test that initialization fails when GOOGLE_API_KEY is not set."""
        from app.core.settings import Settings

        # Mock the Settings class to return a mock with no google_api_key
        mock_settings = Settings()
        mock_settings.google_api_key = None

        with patch(
            "app.features.graph.services.langchain_fact_extractor.Settings",
            return_value=mock_settings,
        ):
            # Should raise ValueError
            with pytest.raises(
                ValueError, match="GOOGLE_API_KEY environment variable not set"
            ):
                LangChainFactExtractor()  # pyright: ignore[reportUnusedCallResult]

    @pytest.mark.asyncio
    async def test_extract_facts_basic_person_info(
        self, extractor: LangChainFactExtractor
    ):
        """Test fact extraction with basic person information."""
        content = "John Doe lives in Paris and works as a Software Engineer at Google."
        entity_identifier = IdentifierPayload(
            type="email", value="john.doe@example.com"
        )

        facts = await extractor.extract_facts(content, entity_identifier)

        # Verify response structure
        assert isinstance(facts, list)
        assert len(facts) > 0  # Should extract at least some facts

        for fact in facts:
            assert isinstance(fact, ExtractedFactDto)

            # Verify data types
            assert isinstance(fact.name, str)
            assert isinstance(fact.type, str)
            assert isinstance(fact.verb, str)
            assert isinstance(fact.confidence_score, (int, float))

            # Verify confidence score range
            assert 0.0 <= fact.confidence_score <= 1.0

            # Verify non-empty strings
            assert fact.name.strip()
            assert fact.type.strip()
            assert fact.verb.strip()

    @pytest.mark.asyncio
    async def test_extract_facts_company_info(self, extractor: LangChainFactExtractor):
        """Test fact extraction with company information."""
        content = "Apple Inc. is headquartered in Cupertino, California and was founded in 1976."
        entity_identifier = IdentifierPayload(type="username", value="AppleInc")

        facts = await extractor.extract_facts(content, entity_identifier)

        assert isinstance(facts, list)
        assert len(facts) > 0

        # Check that relevant facts are extracted
        fact_names = [fact.name for fact in facts]
        assert any(
            location in fact_name
            for fact_name in fact_names
            for location in ["Cupertino", "California"]
        )

        # Verify all facts have required structure
        for fact in facts:
            assert isinstance(fact, ExtractedFactDto)
            assert fact.name
            assert fact.type
            assert fact.verb
            assert 0.0 <= fact.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_extract_facts_empty_content(self, extractor: LangChainFactExtractor):
        """Test fact extraction with minimal/empty content."""
        content = "This is a test entity with minimal information."
        entity_identifier = IdentifierPayload(type="username", value="test-entity-123")

        facts = await extractor.extract_facts(content, entity_identifier)

        # Should still return a list (possibly empty)
        assert isinstance(facts, list)
        # With the new prompt, this should ideally return no facts.
        assert len(facts) == 0

    @pytest.mark.asyncio
    async def test_extract_facts_from_conversational_turn_hobby(
        self, extractor: LangChainFactExtractor
    ):
        """Test fact extraction from a conversational turn about a hobby."""
        content = "I really enjoy hiking on weekends."
        entity_identifier = IdentifierPayload(
            type="email", value="john.doe@example.com"
        )

        facts = await extractor.extract_facts(content, entity_identifier)

        assert isinstance(facts, list)
        assert len(facts) > 0

        fact_names = {str(fact.name).lower() for fact in facts}
        assert "hiking" in fact_names

        # Check for a hobby-related fact
        hobby_fact_found = False
        for fact in facts:
            if str(fact.name).lower() == "hiking":
                assert str(fact.type).lower() in ["hobby", "activity"]
                assert str(fact.verb).lower() in ["enjoys", "likes"]
                hobby_fact_found = True
        assert hobby_fact_found, "Hobby fact about hiking not found"

    @pytest.mark.asyncio
    async def test_extract_facts_from_conversational_turn_sentiment(
        self, extractor: LangChainFactExtractor
    ):
        """Test extracting sentiment as a fact."""
        content = "I don't like Mondays."
        entity_identifier = IdentifierPayload(type="username", value="user123")

        facts = await extractor.extract_facts(content, entity_identifier)

        assert isinstance(facts, list)
        assert len(facts) > 0

        fact_names = {str(fact.name).lower() for fact in facts}
        assert "mondays" in fact_names

        # Check for a sentiment-related fact
        sentiment_fact_found = False
        for fact in facts:
            if str(fact.name).lower() == "mondays":
                assert str(fact.verb).lower() in ["dislikes", "does_not_like"]
                sentiment_fact_found = True
        assert sentiment_fact_found, "Sentiment fact about Mondays not found"

    @pytest.mark.asyncio
    async def test_extract_facts_with_conversational_history(
        self, extractor: LangChainFactExtractor
    ):
        """Test fact extraction from a conversation in Portuguese."""
        history = [
            "ai: Entendido, Mariele. Focar no trabalho para destravar as outras áreas é uma visão estratégica.\n\nQuem vai conduzir esse pilar é o Flávio Augusto, que tem uma experiência gigante em construir negócios e gerar riqueza.\n\nMe diga, o que exatamente no seu trabalho você sente que precisa de mais clareza ou direção nesse momento?"
        ]
        content = "De tomar a decisão correta em uma empresa nova que eu e meu marido vamos abrir. A forma certa de iniciar este novo negócio"
        entity_identifier = IdentifierPayload(type="email", value="mariele@example.com")

        facts = await extractor.extract_facts(
            content, entity_identifier, history=history
        )

        assert isinstance(facts, list)
        assert len(facts) > 0

        # Check that the standardization is working
        for fact in facts:
            # 'name' can be in Portuguese
            assert isinstance(fact.name, str)

            # 'type' and 'verb' must be in English. A simple check is to see if they are ASCII.
            assert str(fact.type).isascii()
            assert str(fact.verb).isascii()

            # Check for core concepts in name
            name_lower = str(fact.name).lower()
            assert "empresa" in name_lower or "negócio" in name_lower

        # Verify all facts have required structure
        for fact in facts:
            assert isinstance(fact, ExtractedFactDto)
            assert fact.name
            assert fact.type
            assert fact.verb
            assert 0.0 <= fact.confidence_score <= 1.0
