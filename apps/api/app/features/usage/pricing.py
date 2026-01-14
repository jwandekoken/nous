"""Cost calculation helpers for token usage events.

We store `cost_usd` at write time so historical events remain stable even if
pricing configs change.
"""

from __future__ import annotations

from decimal import Decimal


def _d(value: float | int | str | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def cost_usd_for_chat(
    *,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    prompt_per_1m_tokens: float | Decimal,
    completion_per_1m_tokens: float | Decimal,
) -> Decimal | None:
    if prompt_tokens is None and completion_tokens is None:
        return None

    cost = Decimal("0")
    if prompt_tokens is not None:
        cost += (_d(prompt_tokens) / _d(1_000_000)) * _d(prompt_per_1m_tokens)
    if completion_tokens is not None:
        cost += (_d(completion_tokens) / _d(1_000_000)) * _d(completion_per_1m_tokens)
    return cost


def cost_usd_for_embedding(
    *,
    total_tokens: int | None,
    per_1m_tokens: float | Decimal,
) -> Decimal | None:
    if total_tokens is None:
        return None
    return (_d(total_tokens) / _d(1_000_000)) * _d(per_1m_tokens)
