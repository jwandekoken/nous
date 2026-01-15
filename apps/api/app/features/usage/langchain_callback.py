"""LangChain callback handler + usage extraction adapter.

This file centralizes LangChain usage extraction because provider-specific
metadata varies by SDK/version. The handler records usage without polluting
feature code with parsing logic.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler

from app.core.settings import get_settings
from app.features.usage.pricing import cost_usd_for_chat, cost_usd_for_embedding
from app.features.usage.tracker import TokenUsageTracker, get_token_usage_tracker


@dataclass(frozen=True, slots=True)
class TokenCounts:
    # Simple, immutable container so we can pass parsed usage around safely.
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


def extract_usage_from_langchain_result(result: Any) -> TokenCounts | None:
    """Extract token usage counts from common LangChain result shapes."""
    # LangChain responses differ across runnables and providers, so we probe
    # several known locations in priority order.
    if result is None:
        return None

    # Some adapters expose usage directly as a mapping-like object.
    usage = _extract_usage_from_mapping(_as_mapping(result))
    if usage is not None:
        return usage

    # LC commonly tucks usage under "llm_output".
    llm_output = getattr(result, "llm_output", None)
    usage = _extract_usage_from_mapping(_as_mapping(llm_output))
    if usage is not None:
        return usage

    # For chat models, usage may be attached to each generation/message.
    generations = getattr(result, "generations", None)
    for generation in _iter_generations(generations):
        usage = _extract_usage_from_generation(generation)
        if usage is not None:
            return usage

    return None


class TokenUsageCallbackHandler(AsyncCallbackHandler):
    """Async handler that records token usage for chat model calls."""

    def __init__(
        self,
        *,
        feature: str,
        operation: str,
        tracker: TokenUsageTracker | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        # Feature + operation let us slice costs by domain later.
        self._feature = feature
        self._operation = operation
        # Resolve the tracker once to keep callback overhead low.
        self._tracker = tracker or get_token_usage_tracker()
        # Allow callers to override provider/model if they already know them.
        self._provider = provider
        self._model = model
        # We track input size for fallback metrics when token counts are missing.
        self._input_chars: int | None = None

    async def on_llm_start(
        self, serialized: Mapping[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        # For non-chat LLMs, LangChain gives us prompt strings.
        self._input_chars = _sum_prompt_chars(prompts)
        self._maybe_set_model_provider(serialized, kwargs)

    async def on_chat_model_start(
        self,
        serialized: Mapping[str, Any],
        messages: list[list[Any]],
        **kwargs: Any,
    ) -> None:
        # For chat models, we compute input size by walking message content.
        self._input_chars = _sum_message_chars(messages)
        self._maybe_set_model_provider(serialized, kwargs)

    async def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        # Extract usage if available; we still record char counts as fallback.
        usage = extract_usage_from_langchain_result(response)
        output_chars = _extract_output_chars(response)
        await self._record_event(
            usage=usage,
            output_chars=output_chars,
            status="ok",
            error_type=None,
        )

    async def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        # We record errors with no tokens to keep the audit trail complete.
        await self._record_event(
            usage=None,
            output_chars=None,
            status="error",
            error_type=type(error).__name__,
        )

    def _maybe_set_model_provider(
        self, serialized: Mapping[str, Any], kwargs: Mapping[str, Any]
    ) -> None:
        # Model/provider are best-effort: we only fill them if not provided.
        if self._model is None:
            self._model = _extract_model_name(serialized, kwargs)
        if self._provider is None:
            self._provider = _infer_provider(serialized, self._model)

    async def _record_event(
        self,
        *,
        usage: TokenCounts | None,
        output_chars: int | None,
        status: str,
        error_type: str | None,
    ) -> None:
        try:
            # Convert parsed usage into explicit fields for the repository.
            prompt_tokens = usage.prompt_tokens if usage else None
            completion_tokens = usage.completion_tokens if usage else None
            total_tokens = usage.total_tokens if usage else None

            # Cost is computed at write time so historical events are stable.
            cost_usd = _compute_cost_usd(
                model=self._model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

            await self._tracker.record_chat(
                feature=self._feature,
                operation=self._operation,
                provider=self._provider,
                model=self._model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                input_chars=self._input_chars,
                output_chars=output_chars,
                cost_usd=cost_usd,
                status=status,
                error_type=error_type,
            )
        except Exception:
            # Never let usage tracking fail the primary request path.
            return


def _compute_cost_usd(
    *,
    model: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
) -> Any:
    # Cost depends on the model pricing config; if missing, skip.
    if not model:
        return None

    settings = get_settings()
    model_pricing = settings.model_pricing.get(model)
    if not model_pricing:
        return None

    if (
        "prompt_per_1m_tokens" in model_pricing
        or "completion_per_1m_tokens" in model_pricing
    ):
        # Chat pricing uses prompt/completion rates when available.
        return cost_usd_for_chat(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            prompt_per_1m_tokens=model_pricing.get("prompt_per_1m_tokens", 0.0),
            completion_per_1m_tokens=model_pricing.get("completion_per_1m_tokens", 0.0),
        )

    if "per_1m_tokens" in model_pricing:
        # Embedding pricing is typically a single per-token rate.
        combined_tokens = total_tokens
        if (
            combined_tokens is None
            and prompt_tokens is not None
            and completion_tokens is not None
        ):
            combined_tokens = prompt_tokens + completion_tokens
        return cost_usd_for_embedding(
            total_tokens=combined_tokens,
            per_1m_tokens=model_pricing.get("per_1m_tokens", 0.0),
        )

    return None


def _extract_usage_from_generation(generation: Any) -> TokenCounts | None:
    # Generations can store usage in message or generation info, depending on LC.
    message = getattr(generation, "message", None)
    if message is not None:
        usage = _extract_usage_from_mapping(
            _as_mapping(getattr(message, "usage_metadata", None))
        )
        if usage is not None:
            return usage
        usage = _extract_usage_from_mapping(
            _as_mapping(getattr(message, "response_metadata", None))
        )
        if usage is not None:
            return usage

    generation_info = getattr(generation, "generation_info", None)
    return _extract_usage_from_mapping(_as_mapping(generation_info))


def _extract_usage_from_mapping(
    mapping: Mapping[str, Any] | None,
) -> TokenCounts | None:
    # Normalize to a set of known key names across providers.
    if not mapping:
        return None

    # Some providers nest usage under "usage" or "usage_metadata".
    for nested_key in ("token_usage", "usage", "usage_metadata"):
        nested = mapping.get(nested_key)
        nested_usage = _extract_usage_from_mapping(_as_mapping(nested))
        if nested_usage is not None:
            return nested_usage

    prompt_tokens = _first_int(
        mapping,
        [
            "prompt_tokens",
            "input_tokens",
            "promptTokenCount",
            "inputTokenCount",
        ],
    )
    completion_tokens = _first_int(
        mapping,
        [
            "completion_tokens",
            "output_tokens",
            "completionTokenCount",
            "outputTokenCount",
            "candidatesTokenCount",
        ],
    )
    total_tokens = _first_int(
        mapping,
        [
            "total_tokens",
            "totalTokenCount",
        ],
    )

    if prompt_tokens is None and completion_tokens is None and total_tokens is None:
        return None

    # Prefer a total if missing but both components exist.
    if (
        total_tokens is None
        and prompt_tokens is not None
        and completion_tokens is not None
    ):
        total_tokens = prompt_tokens + completion_tokens

    return TokenCounts(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


def _extract_model_name(
    serialized: Mapping[str, Any], kwargs: Mapping[str, Any]
) -> str | None:
    # Model name appears in different places based on LC version and adapter.
    for source in (
        kwargs,
        kwargs.get("invocation_params"),
        serialized.get("kwargs"),
        serialized,
    ):
        if isinstance(source, Mapping):
            for key in ("model", "model_name", "model_id"):
                value = source.get(key)
                if isinstance(value, str):
                    return value
    return None


def _infer_provider(serialized: Mapping[str, Any], model: str | None) -> str | None:
    # Provider is heuristically inferred to avoid coupling to SDK specifics.
    if model:
        lowered_model = model.lower()
        if "gemini" in lowered_model:
            return "google"
        if "openai" in lowered_model:
            return "openai"
        if "anthropic" in lowered_model:
            return "anthropic"

    name = serialized.get("name")
    if not name:
        serialized_id = serialized.get("id")
        if isinstance(serialized_id, list) and serialized_id:
            name = serialized_id[-1]

    if isinstance(name, str):
        lowered = name.lower()
        if "google" in lowered or "gemini" in lowered:
            return "google"
        if "openai" in lowered:
            return "openai"
        if "anthropic" in lowered:
            return "anthropic"

    return None


def _sum_prompt_chars(prompts: Iterable[str]) -> int:
    # Simple fallback metric when token counts are unavailable.
    return sum(len(prompt) for prompt in prompts if prompt is not None)


def _sum_message_chars(messages: list[list[Any]]) -> int:
    # For chat, aggregate all message content into a single char count.
    total = 0
    for thread in messages:
        for message in thread:
            total += _content_length(getattr(message, "content", message))
    return total


def _extract_output_chars(result: Any) -> int | None:
    # Output size can be derived from generation text or message content.
    generations = getattr(result, "generations", None)
    if not generations:
        return None

    total = 0
    seen = False
    for generation in _iter_generations(generations):
        seen = True
        text = getattr(generation, "text", None)
        if isinstance(text, str):
            total += len(text)
            continue

        message = getattr(generation, "message", None)
        if message is not None:
            total += _content_length(getattr(message, "content", ""))

    return total if seen else None


def _iter_generations(generations: Any) -> Iterable[Any]:
    # LangChain sometimes nests generations as lists-of-lists.
    if not generations:
        return []
    for item in generations:
        if isinstance(item, list):
            for sub in item:
                yield sub
        else:
            yield item


def _content_length(value: Any) -> int:
    # Handles text, structured message parts, and other content shapes.
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value)
    if isinstance(value, list):
        total = 0
        for part in value:
            if isinstance(part, str):
                total += len(part)
            elif isinstance(part, Mapping):
                text = part.get("text")
                if isinstance(text, str):
                    total += len(text)
                else:
                    total += len(str(part))
            else:
                total += len(str(part))
        return total
    return len(str(value))


def _first_int(mapping: Mapping[str, Any], keys: list[str]) -> int | None:
    # Normalizes mixed numeric formats without failing on unexpected types.
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                continue
    return None


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    # Convert pydantic models and raw objects into a mapping if possible.
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        try:
            result = value.model_dump()
            if isinstance(result, Mapping):
                return result
        except Exception:
            return None
    if hasattr(value, "dict"):
        try:
            result = value.dict()
            if isinstance(result, Mapping):
                return result
        except Exception:
            return None
    return None
