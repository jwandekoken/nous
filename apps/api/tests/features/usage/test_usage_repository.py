"""Tests for Usage API endpoints."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import Tenant
from app.features.usage.models import TokenUsageEvent
from app.features.usage.usage_repository import UsageRepository


@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        age_graph_name="test_graph",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def another_tenant(db_session: AsyncSession) -> Tenant:
    """Create another tenant for isolation tests."""
    tenant = Tenant(
        id=uuid4(),
        name="Another Tenant",
        age_graph_name="another_graph",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def usage_events(
    db_session: AsyncSession, test_tenant: Tenant
) -> list[TokenUsageEvent]:
    """Create sample usage events for testing."""
    events = [
        TokenUsageEvent(
            id=uuid4(),
            created_at=datetime(2026, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
            request_id=uuid4(),
            tenant_id=test_tenant.id,
            actor_type="api_key",
            actor_id=uuid4(),
            feature="graph",
            operation="fact_extract",
            endpoint="/api/v1/graph/assimilate",
            provider="google",
            model="gemini-2.5-flash",
            prompt_tokens=1000,
            completion_tokens=200,
            total_tokens=1200,
            input_chars=5000,
            output_chars=1000,
            cost_usd=Decimal("0.0015"),
            status="ok",
            error_type=None,
        ),
        TokenUsageEvent(
            id=uuid4(),
            created_at=datetime(2026, 1, 10, 11, 0, 0, tzinfo=timezone.utc),
            request_id=uuid4(),
            tenant_id=test_tenant.id,
            actor_type="user",
            actor_id=uuid4(),
            feature="graph",
            operation="entity_summary",
            endpoint="/api/v1/graph/entities/lookup/summary",
            provider="google",
            model="gemini-2.5-flash",
            prompt_tokens=800,
            completion_tokens=300,
            total_tokens=1100,
            input_chars=4000,
            output_chars=1500,
            cost_usd=Decimal("0.0012"),
            status="ok",
            error_type=None,
        ),
        TokenUsageEvent(
            id=uuid4(),
            created_at=datetime(2026, 1, 11, 9, 0, 0, tzinfo=timezone.utc),
            request_id=uuid4(),
            tenant_id=test_tenant.id,
            actor_type="api_key",
            actor_id=uuid4(),
            feature="graph",
            operation="fact_extract",
            endpoint="/api/v1/graph/assimilate",
            provider="google",
            model="gemini-2.5-flash",
            prompt_tokens=1500,
            completion_tokens=400,
            total_tokens=1900,
            input_chars=7500,
            output_chars=2000,
            cost_usd=Decimal("0.0020"),
            status="error",
            error_type="RateLimitError",
        ),
    ]
    for event in events:
        db_session.add(event)
    await db_session.commit()
    return events


@pytest_asyncio.fixture
async def other_tenant_events(
    db_session: AsyncSession, another_tenant: Tenant
) -> list[TokenUsageEvent]:
    """Create usage events for another tenant (isolation test)."""
    events = [
        TokenUsageEvent(
            id=uuid4(),
            created_at=datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc),
            request_id=uuid4(),
            tenant_id=another_tenant.id,
            actor_type="api_key",
            actor_id=uuid4(),
            feature="graph",
            operation="fact_extract",
            endpoint="/api/v1/graph/assimilate",
            provider="google",
            model="gemini-2.5-flash",
            prompt_tokens=5000,
            completion_tokens=1000,
            total_tokens=6000,
            input_chars=25000,
            output_chars=5000,
            cost_usd=Decimal("0.0075"),
            status="ok",
            error_type=None,
        ),
    ]
    for event in events:
        db_session.add(event)
    await db_session.commit()
    return events


class TestUsageRepositoryGetEvents:
    """Tests for UsageRepository.get_events_for_tenant."""

    @pytest.mark.asyncio
    async def test_returns_events_for_tenant(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        usage_events: list[TokenUsageEvent],
    ) -> None:
        """Should return events for the specified tenant."""
        repo = UsageRepository()
        events, total = await repo.get_events_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )

        assert total == 3
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_filters_by_date_range(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        usage_events: list[TokenUsageEvent],
    ) -> None:
        """Should filter events by date range."""
        repo = UsageRepository()
        events, total = await repo.get_events_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 10),
            to_date=date(2026, 1, 10),
        )

        assert total == 2  # Only events on Jan 10

    @pytest.mark.asyncio
    async def test_filters_by_operation(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        usage_events: list[TokenUsageEvent],
    ) -> None:
        """Should filter events by operation."""
        repo = UsageRepository()
        events, total = await repo.get_events_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
            operation="fact_extract",
        )

        assert total == 2
        for event in events:
            assert event.operation == "fact_extract"

    @pytest.mark.asyncio
    async def test_filters_by_status(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        usage_events: list[TokenUsageEvent],
    ) -> None:
        """Should filter events by status."""
        repo = UsageRepository()
        events, total = await repo.get_events_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
            status="error",
        )

        assert total == 1
        assert events[0].status == "error"

    @pytest.mark.asyncio
    async def test_pagination(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        usage_events: list[TokenUsageEvent],
    ) -> None:
        """Should paginate results correctly."""
        repo = UsageRepository()
        events, total = await repo.get_events_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
            page=1,
            limit=2,
        )

        assert total == 3  # Total count is still 3
        assert len(events) == 2  # But only 2 returned

    @pytest.mark.asyncio
    async def test_tenant_isolation(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        another_tenant: Tenant,
        usage_events: list[TokenUsageEvent],
        other_tenant_events: list[TokenUsageEvent],
    ) -> None:
        """Should only return events for the specified tenant."""
        repo = UsageRepository()
        events, total = await repo.get_events_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )

        assert total == 3
        for event in events:
            assert event.tenant_id == test_tenant.id


class TestUsageRepositoryGetSummary:
    """Tests for UsageRepository.get_summary_for_tenant."""

    @pytest.mark.asyncio
    async def test_returns_aggregated_totals(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        usage_events: list[TokenUsageEvent],
    ) -> None:
        """Should return aggregated totals."""
        repo = UsageRepository()
        summary = await repo.get_summary_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )

        expected_tokens = 1200 + 1100 + 1900  # sum of all total_tokens
        expected_cost = Decimal("0.0015") + Decimal("0.0012") + Decimal("0.0020")

        assert summary["total_tokens"] == expected_tokens
        assert summary["total_cost_usd"] == expected_cost

    @pytest.mark.asyncio
    async def test_returns_breakdown_by_day(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        usage_events: list[TokenUsageEvent],
    ) -> None:
        """Should return breakdown by day."""
        repo = UsageRepository()
        summary = await repo.get_summary_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )

        assert len(summary["by_day"]) == 2  # Jan 10 and Jan 11
        dates = [d["date"] for d in summary["by_day"]]
        assert date(2026, 1, 10) in dates
        assert date(2026, 1, 11) in dates

    @pytest.mark.asyncio
    async def test_returns_breakdown_by_operation(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        usage_events: list[TokenUsageEvent],
    ) -> None:
        """Should return breakdown by operation."""
        repo = UsageRepository()
        summary = await repo.get_summary_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )

        operations = {op["operation"] for op in summary["by_operation"]}
        assert "fact_extract" in operations
        assert "entity_summary" in operations

    @pytest.mark.asyncio
    async def test_filters_by_operation(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        usage_events: list[TokenUsageEvent],
    ) -> None:
        """Should filter by operation."""
        repo = UsageRepository()
        summary = await repo.get_summary_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
            operation="fact_extract",
        )

        expected_tokens = 1200 + 1900  # only fact_extract events
        assert summary["total_tokens"] == expected_tokens

    @pytest.mark.asyncio
    async def test_tenant_isolation(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        another_tenant: Tenant,
        usage_events: list[TokenUsageEvent],
        other_tenant_events: list[TokenUsageEvent],
    ) -> None:
        """Should only aggregate events for the specified tenant."""
        repo = UsageRepository()
        summary = await repo.get_summary_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )

        # Should NOT include other_tenant's 6000 tokens
        expected_tokens = 1200 + 1100 + 1900
        assert summary["total_tokens"] == expected_tokens

    @pytest.mark.asyncio
    async def test_empty_result(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> None:
        """Should return zeros when no events exist."""
        repo = UsageRepository()
        summary = await repo.get_summary_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )

        assert summary["total_tokens"] == 0
        assert summary["total_cost_usd"] == 0
        assert summary["by_day"] == []
        assert summary["by_operation"] == []
