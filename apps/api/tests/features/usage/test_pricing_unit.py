"""Unit tests for pricing.py.

These tests verify cost calculation helpers for token usage events.
"""

from __future__ import annotations

from decimal import Decimal

from app.features.usage.pricing import cost_usd_for_chat, cost_usd_for_embedding


class TestCostUsdForChat:
    """Tests for cost_usd_for_chat function."""

    def test_cost_usd_for_chat_computes_correctly(self) -> None:
        """Should compute cost correctly with both prompt and completion tokens."""
        cost = cost_usd_for_chat(
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            prompt_per_1m_tokens=0.075,
            completion_per_1m_tokens=0.30,
        )

        # 1M * $0.075 + 1M * $0.30 = $0.375
        assert cost == Decimal("0.375")

    def test_cost_usd_for_chat_returns_none_when_both_tokens_none(self) -> None:
        """Should return None when both prompt and completion tokens are None."""
        cost = cost_usd_for_chat(
            prompt_tokens=None,
            completion_tokens=None,
            prompt_per_1m_tokens=0.075,
            completion_per_1m_tokens=0.30,
        )

        assert cost is None

    def test_cost_usd_for_chat_handles_partial_prompt_only(self) -> None:
        """Should compute cost when only prompt tokens are provided."""
        cost = cost_usd_for_chat(
            prompt_tokens=1_000_000,
            completion_tokens=None,
            prompt_per_1m_tokens=0.075,
            completion_per_1m_tokens=0.30,
        )

        # 1M * $0.075 = $0.075
        assert cost == Decimal("0.075")

    def test_cost_usd_for_chat_handles_partial_completion_only(self) -> None:
        """Should compute cost when only completion tokens are provided."""
        cost = cost_usd_for_chat(
            prompt_tokens=None,
            completion_tokens=1_000_000,
            prompt_per_1m_tokens=0.075,
            completion_per_1m_tokens=0.30,
        )

        # 1M * $0.30 = $0.30
        assert cost == Decimal("0.30")

    def test_cost_usd_for_chat_handles_small_token_counts(self) -> None:
        """Should compute cost correctly for small token counts."""
        cost = cost_usd_for_chat(
            prompt_tokens=1000,
            completion_tokens=500,
            prompt_per_1m_tokens=0.075,
            completion_per_1m_tokens=0.30,
        )

        # 1000 * $0.075/1M + 500 * $0.30/1M = $0.000075 + $0.00015 = $0.000225
        expected = Decimal("0.000075") + Decimal("0.00015")
        assert cost == expected

    def test_cost_usd_for_chat_handles_decimal_rates(self) -> None:
        """Should handle Decimal rates correctly."""
        cost = cost_usd_for_chat(
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            prompt_per_1m_tokens=Decimal("0.075"),
            completion_per_1m_tokens=Decimal("0.30"),
        )

        assert cost == Decimal("0.375")


class TestCostUsdForEmbedding:
    """Tests for cost_usd_for_embedding function."""

    def test_cost_usd_for_embedding_computes_correctly(self) -> None:
        """Should compute cost correctly for embedding tokens."""
        cost = cost_usd_for_embedding(
            total_tokens=1_000_000,
            per_1m_tokens=0.10,
        )

        # 1M * $0.10 = $0.10
        assert cost == Decimal("0.10")

    def test_cost_usd_for_embedding_returns_none_when_tokens_none(self) -> None:
        """Should return None when total_tokens is None."""
        cost = cost_usd_for_embedding(
            total_tokens=None,
            per_1m_tokens=0.10,
        )

        assert cost is None

    def test_cost_usd_for_embedding_handles_small_token_counts(self) -> None:
        """Should compute cost correctly for small token counts."""
        cost = cost_usd_for_embedding(
            total_tokens=1000,
            per_1m_tokens=0.10,
        )

        # 1000 * $0.10/1M = $0.0001
        assert cost == Decimal("0.0001")

    def test_cost_usd_for_embedding_handles_zero_rate(self) -> None:
        """Should handle zero rate (free tier)."""
        cost = cost_usd_for_embedding(
            total_tokens=1_000_000,
            per_1m_tokens=0.00,
        )

        assert cost == Decimal("0")

    def test_cost_usd_for_embedding_handles_decimal_rate(self) -> None:
        """Should handle Decimal rate correctly."""
        cost = cost_usd_for_embedding(
            total_tokens=1_000_000,
            per_1m_tokens=Decimal("0.10"),
        )

        assert cost == Decimal("0.10")
