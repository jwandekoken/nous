"""Token usage tracker primitives.

This layer is intentionally tiny: it pulls request context from contextvars
and delegates persistence to the repository.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.db.postgres.session import get_db_session
from app.features.usage.context import (
    get_actor_id,
    get_actor_type,
    get_request_id,
    get_request_path,
    get_tenant_id,
)
from app.features.usage.usage_repository import TokenUsageEventCreate, UsageRepository


@dataclass(frozen=True, slots=True)
class TokenUsageRecord:
    feature: str
    operation: str
    provider: str | None = None
    model: str | None = None

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    input_chars: int | None = None
    output_chars: int | None = None

    cost_usd: Decimal | None = None
    status: str = "ok"
    error_type: str | None = None


class TokenUsageTracker(Protocol):
    async def record(self, record: TokenUsageRecord) -> None: ...

    async def record_chat(
        self,
        *,
        feature: str,
        operation: str,
        provider: str | None,
        model: str | None,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        total_tokens: int | None,
        input_chars: int | None,
        output_chars: int | None,
        cost_usd: Decimal | None,
        status: str,
        error_type: str | None,
    ) -> None: ...


class NoopTokenUsageTracker:
    async def record(self, record: TokenUsageRecord) -> None:  # noqa: ARG002
        _ = record
        return

    async def record_chat(
        self,
        *,
        feature: str,
        operation: str,
        provider: str | None,
        model: str | None,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        total_tokens: int | None,
        input_chars: int | None,
        output_chars: int | None,
        cost_usd: Decimal | None,
        status: str,
        error_type: str | None,
    ) -> None:
        _ = (
            feature,
            operation,
            provider,
            model,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            input_chars,
            output_chars,
            cost_usd,
            status,
            error_type,
        )
        return


class PostgresTokenUsageTracker:
    def __init__(
        self,
        *,
        get_session: Callable[
            [], AbstractAsyncContextManager[AsyncSession]
        ] = get_db_session,
        usage_repository: UsageRepository | None = None,
    ) -> None:
        self._get_session: Callable[[], AbstractAsyncContextManager[AsyncSession]] = (
            get_session
        )
        self._repo: UsageRepository = usage_repository or UsageRepository()

    async def record(self, record: TokenUsageRecord) -> None:
        request_id = get_request_id()
        tenant_id = get_tenant_id()

        # If we can't attribute, skip (we never want to fail the main request).
        if request_id is None or tenant_id is None:
            return

        event = TokenUsageEventCreate(
            request_id=request_id,
            tenant_id=tenant_id,
            actor_type=get_actor_type(),
            actor_id=get_actor_id(),
            feature=record.feature,
            operation=record.operation,
            endpoint=get_request_path(),
            provider=record.provider,
            model=record.model,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            total_tokens=record.total_tokens,
            input_chars=record.input_chars,
            output_chars=record.output_chars,
            cost_usd=record.cost_usd,
            status=record.status,
            error_type=record.error_type,
        )

        async with self._get_session() as session:
            await self._repo.insert_token_usage_event(session=session, event=event)
            await session.commit()

    async def record_chat(
        self,
        *,
        feature: str,
        operation: str,
        provider: str | None,
        model: str | None,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        total_tokens: int | None,
        input_chars: int | None,
        output_chars: int | None,
        cost_usd: Decimal | None,
        status: str,
        error_type: str | None,
    ) -> None:
        await self.record(
            TokenUsageRecord(
                feature=feature,
                operation=operation,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                input_chars=input_chars,
                output_chars=output_chars,
                cost_usd=cost_usd,
                status=status,
                error_type=error_type,
            )
        )


def get_token_usage_tracker() -> TokenUsageTracker:
    """Factory that returns a Noop tracker unless enabled."""
    settings = get_settings()
    if not getattr(settings, "token_usage_enabled", False):
        return NoopTokenUsageTracker()
    return PostgresTokenUsageTracker()
