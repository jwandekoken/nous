"""Integration tests for the EmbeddingService.

These tests actually call the Google Embedding API, so they require:
- GOOGLE_API_KEY environment variable to be set
- Internet connection for API calls

These tests verify the API contract after refactoring to google-genai.
"""

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.integration

from app.core.settings import Settings
from app.features.graph.services.embedding_service import (
    EmbeddingBatchResult,
    EmbeddingResult,
    EmbeddingService,
    EmbeddingUsageMetadata,
)
from app.features.usage.tracker import TokenUsageRecord, TokenUsageTracker


class TestEmbeddingServiceAPIContract:
    """Test suite for EmbeddingService API contract.

    These tests use the real Google API to verify the service works correctly.
    """

    @pytest.fixture
    def service(self, test_settings: Settings) -> EmbeddingService:
        """Create an EmbeddingService instance for testing."""
        return EmbeddingService(settings=test_settings)

    def test_initialization_without_api_key_fails(self):
        """Test that initialization fails when GOOGLE_API_KEY is not set."""
        mock_settings = Settings()
        mock_settings.google_api_key = None

        with patch(
            "app.features.graph.services.embedding_service.Settings",
            return_value=mock_settings,
        ):
            with pytest.raises(
                ValueError, match="GOOGLE_API_KEY environment variable not set"
            ):
                EmbeddingService()

    def test_embedding_dim_property(self, service: EmbeddingService):
        """Test that embedding_dim property returns configured value."""
        # Default is 768 per settings
        assert service.embedding_dim == 768

    @pytest.mark.asyncio
    async def test_embed_text_returns_embedding_result(self, service: EmbeddingService):
        """Test that embed_text returns EmbeddingResult with correct dimension."""
        text = "Hello, world! This is a test sentence for embedding."

        result = await service.embed_text(text)

        # Verify it returns EmbeddingResult
        assert isinstance(result, EmbeddingResult)
        assert isinstance(result.embedding, list)
        assert len(result.embedding) == service.embedding_dim
        assert all(isinstance(x, float) for x in result.embedding)

    @pytest.mark.asyncio
    async def test_embed_text_with_different_inputs(self, service: EmbeddingService):
        """Test that embed_text works with various input types."""
        test_cases = [
            "Short text",
            "A longer piece of text that contains more words and information.",
            "Special characters: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "Unicode: 你好世界 مرحبا العالم",
        ]

        for text in test_cases:
            result = await service.embed_text(text)
            assert isinstance(result, EmbeddingResult)
            assert len(result.embedding) == service.embedding_dim

    @pytest.mark.asyncio
    async def test_embed_texts_returns_batch_result(self, service: EmbeddingService):
        """Test that embed_texts returns EmbeddingBatchResult."""
        texts = [
            "First sentence to embed.",
            "Second sentence with different content.",
            "Third sentence about something else entirely.",
        ]

        result = await service.embed_texts(texts)

        # Verify we get EmbeddingBatchResult
        assert isinstance(result, EmbeddingBatchResult)
        assert isinstance(result.embeddings, list)
        assert len(result.embeddings) == len(texts)

        # Verify each embedding has correct dimension
        for embedding in result.embeddings:
            assert isinstance(embedding, list)
            assert len(embedding) == service.embedding_dim
            assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_embed_texts_empty_list(self, service: EmbeddingService):
        """Test that embed_texts handles empty list."""
        result = await service.embed_texts([])

        assert isinstance(result, EmbeddingBatchResult)
        assert len(result.embeddings) == 0

    @pytest.mark.asyncio
    async def test_embeddings_are_deterministic_for_same_input(
        self, service: EmbeddingService
    ):
        """Test that same input produces same embedding (within tolerance)."""
        text = "Consistent input for determinism test."

        result1 = await service.embed_text(text)
        result2 = await service.embed_text(text)

        # Embeddings should be very close (allowing for floating point)
        for e1, e2 in zip(result1.embedding, result2.embedding):
            assert abs(e1 - e2) < 1e-6

    @pytest.mark.asyncio
    async def test_different_inputs_produce_different_embeddings(
        self, service: EmbeddingService
    ):
        """Test that different inputs produce different embeddings."""
        result1 = await service.embed_text("The cat sat on the mat.")
        result2 = await service.embed_text("Quantum physics explains atoms.")

        # Calculate cosine similarity - should not be too close
        embedding1 = result1.embedding
        embedding2 = result2.embedding
        dot_product = sum(e1 * e2 for e1, e2 in zip(embedding1, embedding2))
        norm1 = sum(e**2 for e in embedding1) ** 0.5
        norm2 = sum(e**2 for e in embedding2) ** 0.5
        similarity = dot_product / (norm1 * norm2)

        # Different topics should have lower similarity
        assert similarity < 0.9


class TestEmbeddingServiceUsageMetadata:
    """Test suite for usage metadata functionality."""

    @pytest.fixture
    def service(self, test_settings: Settings) -> EmbeddingService:
        """Create an EmbeddingService instance for testing."""
        return EmbeddingService(settings=test_settings)

    @pytest.mark.asyncio
    async def test_embed_text_returns_usage_metadata(self, service: EmbeddingService):
        """Test that embed_text returns usage metadata when available."""
        result = await service.embed_text("Test text for usage metadata")

        # Verify result structure includes usage metadata field
        assert hasattr(result, "usage_metadata")
        # Metadata may be None if provider doesn't return it (non-Vertex)
        if result.usage_metadata is not None:
            assert isinstance(result.usage_metadata, EmbeddingUsageMetadata)

    @pytest.mark.asyncio
    async def test_embed_texts_returns_usage_metadata(self, service: EmbeddingService):
        """Test that embed_texts returns usage metadata when available."""
        result = await service.embed_texts(["Test one", "Test two"])

        assert hasattr(result, "usage_metadata")
        if result.usage_metadata is not None:
            assert isinstance(result.usage_metadata, EmbeddingUsageMetadata)


class TestEmbeddingServiceUsageTracking:
    """Test suite for usage tracker integration."""

    @pytest.fixture
    def service(self, test_settings: Settings) -> EmbeddingService:
        """Create an EmbeddingService instance for testing."""
        return EmbeddingService(settings=test_settings)

    @pytest.fixture
    def mock_tracker(self) -> TokenUsageTracker:
        """Create a mock usage tracker."""
        tracker = AsyncMock(spec=TokenUsageTracker)
        return tracker

    @pytest.mark.asyncio
    async def test_embed_text_calls_tracker(
        self, service: EmbeddingService, mock_tracker: AsyncMock
    ):
        """Test that embed_text calls the tracker with correct data."""
        await service.embed_text(
            "Test text",
            operation="test_operation",
            tracker=mock_tracker,
        )

        # Verify tracker.record was called
        mock_tracker.record.assert_called_once()

        # Verify the record has expected fields
        record = mock_tracker.record.call_args[0][0]
        assert isinstance(record, TokenUsageRecord)
        assert record.feature == "graph"
        assert record.operation == "test_operation"
        assert record.provider == "google"
        assert record.status == "ok"
        assert record.input_chars == len("Test text")

    @pytest.mark.asyncio
    async def test_embed_texts_calls_tracker(
        self, service: EmbeddingService, mock_tracker: AsyncMock
    ):
        """Test that embed_texts calls the tracker with correct data."""
        texts = ["First text", "Second text"]
        await service.embed_texts(
            texts,
            operation="batch_operation",
            tracker=mock_tracker,
        )

        # Verify tracker.record was called
        mock_tracker.record.assert_called_once()

        record = mock_tracker.record.call_args[0][0]
        assert record.operation == "batch_operation"
        assert record.input_chars == sum(len(t) for t in texts)

    @pytest.mark.asyncio
    async def test_tracker_failure_does_not_fail_embedding(
        self, service: EmbeddingService
    ):
        """Test that tracker errors don't affect embedding results."""
        failing_tracker = AsyncMock(spec=TokenUsageTracker)
        failing_tracker.record.side_effect = Exception("Tracker error")

        # Should still return valid result despite tracker failure
        result = await service.embed_text(
            "Test text",
            tracker=failing_tracker,
        )

        assert isinstance(result, EmbeddingResult)
        assert len(result.embedding) == service.embedding_dim

    @pytest.mark.asyncio
    async def test_embed_text_records_token_counts_and_cost(
        self, service: EmbeddingService, mock_tracker: AsyncMock
    ):
        """Verify that prompt_tokens, total_tokens, and cost_usd are recorded."""
        await service.embed_text(
            "Test text for token counting",
            operation="test_usage_metadata",
            tracker=mock_tracker,
        )

        mock_tracker.record.assert_called_once()
        record = mock_tracker.record.call_args[0][0]

        # Verify token counts are captured from Gemini
        assert record.prompt_tokens is not None
        assert record.prompt_tokens > 0
        assert record.total_tokens is not None
        assert record.total_tokens > 0

        # Verify cost is computed (since gemini-embedding-001 is in pricing config)
        assert record.cost_usd is not None
        assert record.cost_usd > 0

    @pytest.mark.asyncio
    async def test_embed_texts_records_token_counts_and_cost(
        self, service: EmbeddingService, mock_tracker: AsyncMock
    ):
        """Verify that batch embedding records token counts and cost."""
        texts = ["First text for batch", "Second text for batch"]
        await service.embed_texts(
            texts,
            operation="test_batch_usage_metadata",
            tracker=mock_tracker,
        )

        mock_tracker.record.assert_called_once()
        record = mock_tracker.record.call_args[0][0]

        # Verify token counts are captured from Gemini
        assert record.prompt_tokens is not None
        assert record.prompt_tokens > 0
        assert record.total_tokens is not None
        assert record.total_tokens > 0

        # Verify cost is computed
        assert record.cost_usd is not None
        assert record.cost_usd > 0
