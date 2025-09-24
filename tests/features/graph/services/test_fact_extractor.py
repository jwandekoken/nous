"""Integration tests for the LangChainFactExtractor service.

These tests actually call the Gemini LLM API, so they require:
- GOOGLE_API_KEY environment variable to be set
- Internet connection for API calls
"""

from unittest.mock import patch

import pytest

from app.features.graph.dtos.knowledge_dto import IdentifierPayload
from app.features.graph.services.fact_extractor import LangChainFactExtractor


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
            "app.features.graph.services.fact_extractor.Settings",
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
        print(f"------> facts: {facts}")

        # Verify response structure
        assert isinstance(facts, list)
        assert len(facts) > 0  # Should extract at least some facts

        for fact in facts:
            assert isinstance(fact, dict)
            assert "name" in fact
            assert "type" in fact
            assert "verb" in fact
            assert "confidence_score" in fact

            # Verify data types
            assert isinstance(fact["name"], str)
            assert isinstance(fact["type"], str)
            assert isinstance(fact["verb"], str)
            assert isinstance(fact["confidence_score"], (int, float))

            # Verify confidence score range
            assert 0.0 <= fact["confidence_score"] <= 1.0

            # Verify non-empty strings
            assert fact["name"].strip()
            assert fact["type"].strip()
            assert fact["verb"].strip()

    @pytest.mark.asyncio
    async def test_extract_facts_company_info(self, extractor: LangChainFactExtractor):
        """Test fact extraction with company information."""
        content = "Apple Inc. is headquartered in Cupertino, California and was founded in 1976."
        entity_identifier = IdentifierPayload(type="username", value="AppleInc")

        facts = await extractor.extract_facts(content, entity_identifier)
        print(f"------> facts: {facts}")

        assert isinstance(facts, list)
        assert len(facts) > 0

        # Check that relevant facts are extracted
        fact_names = [fact["name"] for fact in facts]
        print(f"------> fact_names: {fact_names}")
        assert any(
            location in fact_name
            for fact_name in fact_names
            for location in ["Cupertino", "California"]
        )

        # Verify all facts have required structure
        for fact in facts:
            assert all(
                key in fact for key in ["name", "type", "verb", "confidence_score"]
            )

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
    async def test_extract_facts_multiple_entities(
        self, extractor: LangChainFactExtractor
    ):
        """Test fact extraction when content mentions multiple entities."""
        content = "Alice Johnson works at Microsoft in Seattle. Bob Smith lives in New York and enjoys hiking."
        entity_identifier = IdentifierPayload(
            type="email", value="alice.johnson@example.com"
        )

        facts = await extractor.extract_facts(content, entity_identifier)

        assert isinstance(facts, list)

        # Should focus on facts relevant to the specified entity (Alice)
        # The LLM should prioritize Alice-related facts
        fact_names = {fact["name"] for fact in facts}

        # Should contain Alice-related facts, possibly some general ones
        assert len(facts) > 0

        for fact in facts:
            assert all(
                key in fact for key in ["name", "type", "verb", "confidence_score"]
            )

    @pytest.mark.asyncio
    async def test_extract_facts_different_identifier_types(
        self, extractor: LangChainFactExtractor
    ):
        """Test fact extraction with different identifier types."""
        content = "Sarah Wilson is a Data Scientist with a PhD in Computer Science."
        test_cases = [
            IdentifierPayload(type="email", value="sarah.wilson@example.com"),
            IdentifierPayload(type="username", value="sarah_wilson"),
            IdentifierPayload(type="phone", value="+1-555-0123"),
        ]

        for identifier in test_cases:
            facts = await extractor.extract_facts(content, identifier)

            assert isinstance(facts, list)
            assert len(facts) > 0

            for fact in facts:
                assert all(
                    key in fact for key in ["name", "type", "verb", "confidence_score"]
                )
                assert isinstance(fact["name"], str)
                assert isinstance(fact["type"], str)
                assert isinstance(fact["verb"], str)
                assert isinstance(fact["confidence_score"], (int, float))

    @pytest.mark.asyncio
    async def test_extract_facts_confidence_scores(
        self, extractor: LangChainFactExtractor
    ):
        """Test that confidence scores are properly assigned."""
        content = "Jane Doe is definitely a Senior Engineer and probably lives in San Francisco."
        entity_identifier = IdentifierPayload(
            type="email", value="jane.doe@example.com"
        )

        facts = await extractor.extract_facts(content, entity_identifier)

        assert isinstance(facts, list)
        assert len(facts) > 0

        # All facts should have confidence scores
        for fact in facts:
            confidence = fact["confidence_score"]
            assert isinstance(confidence, (int, float))
            assert 0.0 <= confidence <= 1.0

            # "Definitely" should result in high confidence, "probably" in medium confidence
            # But this is subjective, so we just verify the range

    @pytest.mark.asyncio
    async def test_extract_facts_response_consistency(
        self, extractor: LangChainFactExtractor
    ):
        """Test that the same content produces consistent fact structures."""
        content = "Michael Brown is a Product Manager at Amazon."
        entity_identifier = IdentifierPayload(
            type="email", value="michael.brown@example.com"
        )

        # Run extraction multiple times
        results = []
        for _ in range(3):
            facts = await extractor.extract_facts(content, entity_identifier)
            results.append(facts)

        # All results should have the same structure
        for facts in results:
            assert isinstance(facts, list)
            for fact in facts:
                assert all(
                    key in fact for key in ["name", "type", "verb", "confidence_score"]
                )

        # Note: Due to LLM variability, the exact facts might differ between runs
        # But the structure should always be consistent

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

        fact_names = {fact["name"].lower() for fact in facts}
        assert "hiking" in fact_names

        # Check for a hobby-related fact
        hobby_fact_found = False
        for fact in facts:
            if fact["name"].lower() == "hiking":
                assert fact["type"].lower() in ["hobby", "activity"]
                assert fact["verb"].lower() in ["enjoys", "likes"]
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

        fact_names = {fact["name"].lower() for fact in facts}
        assert "mondays" in fact_names

        # Check for a sentiment-related fact
        sentiment_fact_found = False
        for fact in facts:
            if fact["name"].lower() == "mondays":
                assert fact["verb"].lower() in ["dislikes", "does_not_like"]
                sentiment_fact_found = True
        assert sentiment_fact_found, "Sentiment fact about Mondays not found"

    @pytest.mark.asyncio
    async def test_extract_facts_with_conversational_history(
        self, extractor: LangChainFactExtractor
    ):
        """Test fact extraction using conversational history for context."""
        history = [
            "Other Person: What do you think of the new software update?",
            "Entity: I'm not sure yet, I haven't had a chance to test it.",
            "Other Person: It has a new feature for data visualization.",
        ]
        content = "Oh, I really like that."  # This refers to "data visualization"
        entity_identifier = IdentifierPayload(type="email", value="user@example.com")

        facts = await extractor.extract_facts(
            content, entity_identifier, history=history
        )

        assert isinstance(facts, list)
        assert len(facts) > 0

        # The LLM should be able to connect "that" to "data visualization"
        fact_names = {fact["name"].lower() for fact in facts}
        assert "data visualization" in fact_names

        # Check for the contextual fact
        contextual_fact_found = False
        for fact in facts:
            if fact["name"].lower() == "data visualization":
                assert fact["verb"].lower() in ["likes", "enjoys"]
                contextual_fact_found = True
        assert contextual_fact_found, (
            "Contextual fact about data visualization not found"
        )
