"""Unit tests for langchain_callback.py.

These tests verify the usage extraction adapter and callback handler
without making actual LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.usage.langchain_callback import (
    TokenUsageCallbackHandler,
    extract_usage_from_langchain_result,
)

# =============================================================================
# Test fixtures and helpers
# =============================================================================


@dataclass
class MockMessage:
    """Mock LangChain message with optional usage metadata."""

    content: str
    usage_metadata: dict[str, Any] | None = None
    response_metadata: dict[str, Any] | None = None


@dataclass
class MockGeneration:
    """Mock LangChain generation."""

    text: str
    message: MockMessage | None = None
    generation_info: dict[str, Any] | None = None


@dataclass
class MockLLMResult:
    """Mock LangChain LLM result."""

    generations: list[list[MockGeneration]] | None = None
    llm_output: dict[str, Any] | None = None


# =============================================================================
# Tests: extract_usage_from_langchain_result
# =============================================================================


class TestExtractUsageFromLangchainResult:
    """Tests for the extract_usage_from_langchain_result adapter."""

    def test_extract_usage_from_none_returns_none(self) -> None:
        """Should return None when result is None."""
        assert extract_usage_from_langchain_result(None) is None

    def test_extract_usage_from_direct_mapping(self) -> None:
        """Should extract usage from top-level mapping fields."""
        result = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }
        usage = extract_usage_from_langchain_result(result)

        assert usage is not None
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_extract_usage_from_llm_output_nested(self) -> None:
        """Should extract usage nested under llm_output."""
        result = MockLLMResult(
            llm_output={
                "token_usage": {
                    "prompt_tokens": 200,
                    "completion_tokens": 100,
                    "total_tokens": 300,
                }
            }
        )
        usage = extract_usage_from_langchain_result(result)

        assert usage is not None
        assert usage.prompt_tokens == 200
        assert usage.completion_tokens == 100
        assert usage.total_tokens == 300

    def test_extract_usage_from_generations_with_message_usage_metadata(self) -> None:
        """Should extract usage from generation message usage_metadata."""
        message = MockMessage(
            content="response",
            usage_metadata={
                "prompt_tokens": 150,
                "completion_tokens": 75,
                "total_tokens": 225,
            },
        )
        generation = MockGeneration(text="response", message=message)
        result = MockLLMResult(generations=[[generation]])

        usage = extract_usage_from_langchain_result(result)

        assert usage is not None
        assert usage.prompt_tokens == 150
        assert usage.completion_tokens == 75
        assert usage.total_tokens == 225

    def test_extract_usage_from_generations_with_response_metadata(self) -> None:
        """Should extract usage from generation message response_metadata."""
        message = MockMessage(
            content="response",
            response_metadata={
                "usage": {
                    "prompt_tokens": 120,
                    "completion_tokens": 60,
                    "total_tokens": 180,
                }
            },
        )
        generation = MockGeneration(text="response", message=message)
        result = MockLLMResult(generations=[[generation]])

        usage = extract_usage_from_langchain_result(result)

        assert usage is not None
        assert usage.prompt_tokens == 120
        assert usage.completion_tokens == 60
        assert usage.total_tokens == 180

    def test_extract_usage_handles_gemini_style_keys(self) -> None:
        """Should handle Gemini-style token count keys (promptTokenCount, etc.)."""
        result = {
            "promptTokenCount": 500,
            "candidatesTokenCount": 250,
            "totalTokenCount": 750,
        }
        usage = extract_usage_from_langchain_result(result)

        assert usage is not None
        assert usage.prompt_tokens == 500
        assert usage.completion_tokens == 250
        assert usage.total_tokens == 750

    def test_extract_usage_handles_openai_style_keys(self) -> None:
        """Should handle OpenAI-style keys (prompt_tokens, completion_tokens)."""
        result = {
            "usage": {
                "prompt_tokens": 400,
                "completion_tokens": 200,
                "total_tokens": 600,
            }
        }
        usage = extract_usage_from_langchain_result(result)

        assert usage is not None
        assert usage.prompt_tokens == 400
        assert usage.completion_tokens == 200
        assert usage.total_tokens == 600

    def test_extract_usage_computes_total_when_missing(self) -> None:
        """Should compute total_tokens when only prompt and completion are present."""
        result = {
            "prompt_tokens": 300,
            "completion_tokens": 150,
            # total_tokens intentionally missing
        }
        usage = extract_usage_from_langchain_result(result)

        assert usage is not None
        assert usage.prompt_tokens == 300
        assert usage.completion_tokens == 150
        assert usage.total_tokens == 450  # computed

    def test_extract_usage_returns_none_when_no_token_fields(self) -> None:
        """Should return None when no token-related fields are present."""
        result = {"some_other_field": "value", "another_field": 123}
        usage = extract_usage_from_langchain_result(result)

        assert usage is None

    def test_extract_usage_handles_input_output_tokens_keys(self) -> None:
        """Should handle input_tokens/output_tokens style keys."""
        result = {
            "input_tokens": 250,
            "output_tokens": 125,
        }
        usage = extract_usage_from_langchain_result(result)

        assert usage is not None
        assert usage.prompt_tokens == 250
        assert usage.completion_tokens == 125
        assert usage.total_tokens == 375  # computed


# =============================================================================
# Tests: TokenUsageCallbackHandler
# =============================================================================


class TestTokenUsageCallbackHandler:
    """Tests for the TokenUsageCallbackHandler."""

    @pytest.fixture
    def mock_tracker(self) -> AsyncMock:
        """Create a mock token usage tracker."""
        return AsyncMock()

    @pytest.fixture
    def handler(self, mock_tracker: AsyncMock) -> TokenUsageCallbackHandler:
        """Create a handler with mocked tracker."""
        return TokenUsageCallbackHandler(
            feature="graph",
            operation="test_operation",
            tracker=mock_tracker,
        )

    @pytest.mark.asyncio
    async def test_on_llm_end_records_event_with_ok_status(
        self, handler: TokenUsageCallbackHandler, mock_tracker: AsyncMock
    ) -> None:
        """Should record event with ok status on successful LLM call."""
        # Simulate LLM start to capture input chars
        await handler.on_llm_start({}, ["test prompt"])

        # Simulate LLM end with usage metadata
        response = MockLLMResult(
            llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 5}}
        )
        await handler.on_llm_end(response)

        mock_tracker.record_chat.assert_called_once()
        call_kwargs = mock_tracker.record_chat.call_args.kwargs
        assert call_kwargs["status"] == "ok"
        assert call_kwargs["error_type"] is None
        assert call_kwargs["prompt_tokens"] == 10
        assert call_kwargs["completion_tokens"] == 5

    @pytest.mark.asyncio
    async def test_on_llm_error_records_event_with_error_status_and_error_type(
        self, handler: TokenUsageCallbackHandler, mock_tracker: AsyncMock
    ) -> None:
        """Should record event with error status and error type on LLM error."""
        await handler.on_llm_start({}, ["test prompt"])
        await handler.on_llm_error(ValueError("test error"))

        mock_tracker.record_chat.assert_called_once()
        call_kwargs = mock_tracker.record_chat.call_args.kwargs
        assert call_kwargs["status"] == "error"
        assert call_kwargs["error_type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_input_chars_captured_from_prompts(
        self, handler: TokenUsageCallbackHandler, mock_tracker: AsyncMock
    ) -> None:
        """Should capture input chars from prompts via on_llm_start."""
        prompts = ["Hello", "World"]  # 5 + 5 = 10 chars
        await handler.on_llm_start({}, prompts)
        await handler.on_llm_end(MockLLMResult())

        call_kwargs = mock_tracker.record_chat.call_args.kwargs
        assert call_kwargs["input_chars"] == 10

    @pytest.mark.asyncio
    async def test_input_chars_captured_from_chat_messages(
        self, handler: TokenUsageCallbackHandler, mock_tracker: AsyncMock
    ) -> None:
        """Should capture input chars from messages via on_chat_model_start."""
        messages = [[MockMessage(content="Hello there")]]  # 11 chars
        await handler.on_chat_model_start({}, messages)
        await handler.on_llm_end(MockLLMResult())

        call_kwargs = mock_tracker.record_chat.call_args.kwargs
        assert call_kwargs["input_chars"] == 11

    @pytest.mark.asyncio
    async def test_output_chars_extracted_from_generations(
        self, handler: TokenUsageCallbackHandler, mock_tracker: AsyncMock
    ) -> None:
        """Should extract output chars from generation text."""
        generation = MockGeneration(text="Response text")  # 13 chars
        response = MockLLMResult(generations=[[generation]])

        await handler.on_llm_start({}, ["prompt"])
        await handler.on_llm_end(response)

        call_kwargs = mock_tracker.record_chat.call_args.kwargs
        assert call_kwargs["output_chars"] == 13

    @pytest.mark.asyncio
    async def test_cost_computed_from_pricing_config(
        self, mock_tracker: AsyncMock
    ) -> None:
        """Should compute cost when pricing config exists for model."""
        mock_settings = MagicMock()
        mock_settings.model_pricing = {
            "gemini-2.5-flash": {
                "prompt_per_1m_tokens": 0.075,
                "completion_per_1m_tokens": 0.30,
            }
        }

        with patch(
            "app.features.usage.langchain_callback.get_settings",
            return_value=mock_settings,
        ):
            handler = TokenUsageCallbackHandler(
                feature="graph",
                operation="test",
                tracker=mock_tracker,
                model="gemini-2.5-flash",
            )
            response = MockLLMResult(
                llm_output={
                    "token_usage": {
                        "prompt_tokens": 1_000_000,
                        "completion_tokens": 1_000_000,
                    }
                }
            )
            await handler.on_llm_start({}, ["prompt"])
            await handler.on_llm_end(response)

        call_kwargs = mock_tracker.record_chat.call_args.kwargs
        # 1M prompt * $0.075 + 1M completion * $0.30 = $0.375
        assert call_kwargs["cost_usd"] == Decimal("0.375")

    @pytest.mark.asyncio
    async def test_cost_is_none_when_model_not_in_pricing(
        self, mock_tracker: AsyncMock
    ) -> None:
        """Should return None cost when model not in pricing config."""
        mock_settings = MagicMock()
        mock_settings.model_pricing = {}  # No pricing configured

        with patch(
            "app.features.usage.langchain_callback.get_settings",
            return_value=mock_settings,
        ):
            handler = TokenUsageCallbackHandler(
                feature="graph",
                operation="test",
                tracker=mock_tracker,
                model="unknown-model",
            )
            response = MockLLMResult(
                llm_output={
                    "token_usage": {"prompt_tokens": 100, "completion_tokens": 50}
                }
            )
            await handler.on_llm_start({}, ["prompt"])
            await handler.on_llm_end(response)

        call_kwargs = mock_tracker.record_chat.call_args.kwargs
        assert call_kwargs["cost_usd"] is None

    @pytest.mark.asyncio
    async def test_model_and_provider_inferred_from_serialized(
        self, mock_tracker: AsyncMock
    ) -> None:
        """Should infer model and provider from serialized data."""
        mock_settings = MagicMock()
        mock_settings.model_pricing = {}

        with patch(
            "app.features.usage.langchain_callback.get_settings",
            return_value=mock_settings,
        ):
            handler = TokenUsageCallbackHandler(
                feature="graph",
                operation="test",
                tracker=mock_tracker,
            )
            serialized = {"kwargs": {"model": "gemini-2.5-flash"}}
            await handler.on_llm_start(serialized, ["prompt"])
            await handler.on_llm_end(MockLLMResult())

        call_kwargs = mock_tracker.record_chat.call_args.kwargs
        assert call_kwargs["model"] == "gemini-2.5-flash"
        assert call_kwargs["provider"] == "google"

    @pytest.mark.asyncio
    async def test_record_failure_does_not_raise(self, mock_tracker: AsyncMock) -> None:
        """Should swallow exceptions to avoid failing main request."""
        mock_tracker.record_chat.side_effect = Exception("DB error")

        mock_settings = MagicMock()
        mock_settings.model_pricing = {}

        with patch(
            "app.features.usage.langchain_callback.get_settings",
            return_value=mock_settings,
        ):
            handler = TokenUsageCallbackHandler(
                feature="graph",
                operation="test",
                tracker=mock_tracker,
            )
            # Should not raise
            await handler.on_llm_start({}, ["prompt"])
            await handler.on_llm_end(MockLLMResult())

        # Verify we attempted to record
        mock_tracker.record_chat.assert_called_once()
