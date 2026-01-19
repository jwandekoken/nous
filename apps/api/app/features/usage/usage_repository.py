"""Postgres repository for token usage events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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

    async def get_events_for_tenant(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID,
        from_date: date,
        to_date: date,
        operation: str | None = None,
        model: str | None = None,
        actor_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[TokenUsageEvent], int]:
        """Get paginated events for a tenant within a date range.

        Returns:
            Tuple of (events list, total count).
        """
        from datetime import datetime, time, timezone

        from sqlalchemy import and_, func, select

        # Build date range bounds (inclusive)
        from_datetime = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        to_datetime = datetime.combine(to_date, time.max, tzinfo=timezone.utc)

        # Base filter conditions
        conditions = [
            TokenUsageEvent.tenant_id == tenant_id,
            TokenUsageEvent.created_at >= from_datetime,
            TokenUsageEvent.created_at <= to_datetime,
        ]

        if operation:
            conditions.append(TokenUsageEvent.operation == operation)
        if model:
            conditions.append(TokenUsageEvent.model == model)
        if actor_type:
            conditions.append(TokenUsageEvent.actor_type == actor_type)
        if status:
            conditions.append(TokenUsageEvent.status == status)

        # Count query
        count_stmt = (
            select(func.count()).select_from(TokenUsageEvent).where(and_(*conditions))
        )
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Data query with pagination
        offset = (page - 1) * limit
        data_stmt = (
            select(TokenUsageEvent)
            .where(and_(*conditions))
            .order_by(TokenUsageEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        data_result = await session.execute(data_stmt)
        events = list(data_result.scalars().all())

        return events, total

    async def get_summary_for_tenant(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID,
        from_date: date,
        to_date: date,
        operation: str | None = None,
        model: str | None = None,
    ) -> dict:
        """Get aggregated summary for a tenant within a date range.

        Returns:
            Dict with total_tokens, total_cost_usd, by_day, by_operation.
        """
        from datetime import datetime, time, timezone

        from sqlalchemy import and_, cast, func, select
        from sqlalchemy.dialects.postgresql import DATE

        # Build date range bounds (inclusive)
        from_datetime = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        to_datetime = datetime.combine(to_date, time.max, tzinfo=timezone.utc)

        # Base filter conditions
        conditions = [
            TokenUsageEvent.tenant_id == tenant_id,
            TokenUsageEvent.created_at >= from_datetime,
            TokenUsageEvent.created_at <= to_datetime,
        ]

        if operation:
            conditions.append(TokenUsageEvent.operation == operation)
        if model:
            conditions.append(TokenUsageEvent.model == model)

        # Total aggregation
        total_stmt = select(
            func.coalesce(func.sum(TokenUsageEvent.total_tokens), 0).label(
                "total_tokens"
            ),
            func.coalesce(func.sum(TokenUsageEvent.cost_usd), 0).label(
                "total_cost_usd"
            ),
        ).where(and_(*conditions))
        total_result = await session.execute(total_stmt)
        total_row = total_result.one()

        # By day aggregation
        by_day_stmt = (
            select(
                cast(TokenUsageEvent.created_at, DATE).label("date"),
                func.coalesce(func.sum(TokenUsageEvent.total_tokens), 0).label(
                    "tokens"
                ),
                func.coalesce(func.sum(TokenUsageEvent.cost_usd), 0).label("cost_usd"),
            )
            .where(and_(*conditions))
            .group_by(cast(TokenUsageEvent.created_at, DATE))
            .order_by(cast(TokenUsageEvent.created_at, DATE))
        )
        by_day_result = await session.execute(by_day_stmt)
        by_day = [
            {"date": row.date, "tokens": row.tokens, "cost_usd": row.cost_usd}
            for row in by_day_result
        ]

        # By operation aggregation
        by_op_stmt = (
            select(
                TokenUsageEvent.operation,
                func.coalesce(func.sum(TokenUsageEvent.total_tokens), 0).label(
                    "tokens"
                ),
                func.coalesce(func.sum(TokenUsageEvent.cost_usd), 0).label("cost_usd"),
            )
            .where(and_(*conditions))
            .group_by(TokenUsageEvent.operation)
            .order_by(func.sum(TokenUsageEvent.total_tokens).desc())
        )
        by_op_result = await session.execute(by_op_stmt)
        by_operation = [
            {"operation": row.operation, "tokens": row.tokens, "cost_usd": row.cost_usd}
            for row in by_op_result
        ]

        return {
            "total_tokens": total_row.total_tokens,
            "total_cost_usd": total_row.total_cost_usd,
            "by_day": by_day,
            "by_operation": by_operation,
        }
