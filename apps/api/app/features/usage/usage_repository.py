"""Postgres repository for token usage events."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.usage.models import TokenUsageEvent


@dataclass(frozen=True, slots=True)
class TokenUsageEventCreate:
    request_id: UUID
    tenant_id: UUID
    actor_type: str
    actor_id: UUID | None
    feature: str
    operation: str
    endpoint: str | None
    provider: str | None
    model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    input_chars: int | None
    output_chars: int | None
    cost_usd: Decimal | None
    status: str
    error_type: str | None


class UsageRepository:
    async def insert_token_usage_event(
        self, *, session: AsyncSession, event: TokenUsageEventCreate
    ) -> None:
        session.add(
            TokenUsageEvent(
                request_id=event.request_id,
                tenant_id=event.tenant_id,
                actor_type=event.actor_type,
                actor_id=event.actor_id,
                feature=event.feature,
                operation=event.operation,
                endpoint=event.endpoint,
                provider=event.provider,
                model=event.model,
                prompt_tokens=event.prompt_tokens,
                completion_tokens=event.completion_tokens,
                total_tokens=event.total_tokens,
                input_chars=event.input_chars,
                output_chars=event.output_chars,
                cost_usd=event.cost_usd,
                status=event.status,
                error_type=event.error_type,
            )
        )
