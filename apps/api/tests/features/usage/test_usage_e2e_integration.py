"""End-to-end integration tests for usage event persistence.

These tests verify that usage events are correctly persisted when
calling the API endpoints that trigger LLM/embedding calls.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio

pytestmark = pytest.mark.integration

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import Tenant
from app.features.usage.context import (
    set_actor_type,
    set_request_id,
    set_request_path,
    set_tenant_id,
)
from app.features.usage.models import TokenUsageEvent
from app.features.usage.tracker import PostgresTokenUsageTracker, TokenUsageRecord
from app.features.usage.usage_repository import UsageRepository


@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        id=uuid4(),
        name="E2E Test Tenant",
        age_graph_name="e2e_test_graph",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


class TestUsageEventPersistence:
    """Tests for end-to-end usage event persistence."""

    @pytest.mark.asyncio
    async def test_tracker_persists_usage_event(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> None:
        """Verify that PostgresTokenUsageTracker persists events to the database."""
        # Set up request context
        request_id = uuid4()
        set_request_id(request_id)
        set_tenant_id(test_tenant.id)
        set_actor_type("api_key")
        set_request_path("/api/v1/graph/assimilate")

        # Create tracker with the test session
        async def get_test_session():
            """Context manager that yields the test session."""

            class SessionContextManager:
                async def __aenter__(self):
                    return db_session

                async def __aexit__(self, *args):
                    pass

            return SessionContextManager()

        # Use the factory directly with real session
        tracker = PostgresTokenUsageTracker(
            get_session=lambda: get_test_session().__aenter__(),  # noqa: E501
        )

        # Record a usage event
        record = TokenUsageRecord(
            feature="graph",
            operation="fact_extract",
            provider="google",
            model="gemini-2.5-flash",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            input_chars=500,
            output_chars=200,
            status="ok",
        )
        await tracker.record(record)

        # Verify the event was persisted
        stmt = select(TokenUsageEvent).where(
            TokenUsageEvent.tenant_id == test_tenant.id
        )
        result = await db_session.execute(stmt)
        events = result.scalars().all()

        assert len(events) == 1
        event = events[0]
        assert event.feature == "graph"
        assert event.operation == "fact_extract"
        assert event.provider == "google"
        assert event.model == "gemini-2.5-flash"
        assert event.prompt_tokens == 100
        assert event.completion_tokens == 50
        assert event.total_tokens == 150
        assert event.status == "ok"

    @pytest.mark.asyncio
    async def test_usage_events_have_correct_tenant_attribution(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> None:
        """Verify that usage events are correctly attributed to the tenant."""
        # Create another tenant
        other_tenant = Tenant(
            id=uuid4(),
            name="Other Tenant",
            age_graph_name="other_graph",
        )
        db_session.add(other_tenant)
        await db_session.commit()

        # Insert events for both tenants directly
        event1 = TokenUsageEvent(
            id=uuid4(),
            request_id=uuid4(),
            tenant_id=test_tenant.id,
            actor_type="api_key",
            feature="graph",
            operation="fact_extract",
            provider="google",
            model="gemini-2.5-flash",
            total_tokens=100,
            status="ok",
        )
        event2 = TokenUsageEvent(
            id=uuid4(),
            request_id=uuid4(),
            tenant_id=other_tenant.id,
            actor_type="api_key",
            feature="graph",
            operation="fact_extract",
            provider="google",
            model="gemini-2.5-flash",
            total_tokens=200,
            status="ok",
        )
        db_session.add(event1)
        db_session.add(event2)
        await db_session.commit()

        # Query for test_tenant only
        repo = UsageRepository()
        events, total = await repo.get_events_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2020, 1, 1),
            to_date=date(2030, 12, 31),
        )

        assert total == 1
        assert events[0].tenant_id == test_tenant.id
        assert events[0].total_tokens == 100

    @pytest.mark.asyncio
    async def test_usage_events_have_correct_operation_tags(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> None:
        """Verify that usage events have correct feature, operation, and endpoint."""
        # Insert event with all tags
        event = TokenUsageEvent(
            id=uuid4(),
            request_id=uuid4(),
            tenant_id=test_tenant.id,
            actor_type="user",
            feature="graph",
            operation="entity_summary",
            endpoint="/api/v1/graph/entities/lookup/summary",
            provider="google",
            model="gemini-2.5-flash",
            total_tokens=150,
            status="ok",
        )
        db_session.add(event)
        await db_session.commit()

        # Query and verify
        repo = UsageRepository()
        events, _ = await repo.get_events_for_tenant(
            session=db_session,
            tenant_id=test_tenant.id,
            from_date=date(2020, 1, 1),
            to_date=date(2030, 12, 31),
        )

        assert len(events) == 1
        assert events[0].feature == "graph"
        assert events[0].operation == "entity_summary"
        assert events[0].endpoint == "/api/v1/graph/entities/lookup/summary"

    @pytest.mark.asyncio
    async def test_tracker_skips_when_context_missing(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Verify that tracker gracefully skips when request_id or tenant_id is missing."""
        from app.features.usage.context import clear_usage_context

        # Clear any existing context
        clear_usage_context()

        # Use actual session factory
        async def get_test_session():
            class SessionContextManager:
                async def __aenter__(self):
                    return db_session

                async def __aexit__(self, *args):
                    pass

            return SessionContextManager()

        tracker = PostgresTokenUsageTracker(
            get_session=lambda: get_test_session().__aenter__(),
        )

        # Record should not raise, but should not persist
        record = TokenUsageRecord(
            feature="graph",
            operation="fact_extract",
            provider="google",
            model="gemini-2.5-flash",
            status="ok",
        )
        await tracker.record(record)  # Should not raise

        # Verify no event was persisted (no tenant context)
        stmt = select(TokenUsageEvent)
        result = await db_session.execute(stmt)
        events = result.scalars().all()
        assert len(events) == 0


class TestNoopTrackerBehavior:
    """Tests for NoopTokenUsageTracker behavior."""

    @pytest.mark.asyncio
    async def test_noop_tracker_does_not_persist(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> None:
        """Verify that NoopTokenUsageTracker does not persist events."""
        from app.features.usage.tracker import NoopTokenUsageTracker

        # Set up context just in case
        set_request_id(uuid4())
        set_tenant_id(test_tenant.id)

        tracker = NoopTokenUsageTracker()
        record = TokenUsageRecord(
            feature="graph",
            operation="fact_extract",
            provider="google",
            model="gemini-2.5-flash",
            status="ok",
        )
        await tracker.record(record)

        # Verify nothing was persisted
        stmt = select(TokenUsageEvent).where(
            TokenUsageEvent.tenant_id == test_tenant.id
        )
        result = await db_session.execute(stmt)
        events = result.scalars().all()
        assert len(events) == 0
