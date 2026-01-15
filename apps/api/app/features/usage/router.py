"""Usage API router for viewing usage events and summaries."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.authorization import TenantInfo, get_tenant_info
from app.db.postgres.session import get_db_session
from app.features.usage.dtos import (
    PaginationMeta,
    UsageEventDTO,
    UsageEventsResponse,
    UsageSummaryByDay,
    UsageSummaryByOperation,
    UsageSummaryPeriod,
    UsageSummaryResponse,
)
from app.features.usage.usage_repository import UsageRepository

router = APIRouter(
    prefix="/usage",
    tags=["usage"],
    dependencies=[Depends(get_tenant_info)],
)

# Shared repository instance
_usage_repository = UsageRepository()


@router.get("/events", response_model=UsageEventsResponse)
async def get_usage_events(
    tenant_info: TenantInfo = Depends(get_tenant_info),
    from_date: date = Query(
        ..., alias="from", description="Start of period (inclusive)"
    ),
    to_date: date = Query(..., alias="to", description="End of period (inclusive)"),
    operation: str | None = Query(None, description="Filter by operation"),
    model: str | None = Query(None, description="Filter by model"),
    actor_type: str | None = Query(
        None, description="Filter by actor type (api_key or user)"
    ),
    status: str | None = Query(None, description="Filter by status (ok or error)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
) -> UsageEventsResponse:
    """Get paginated usage events for the authenticated tenant.

    Returns a list of usage events with pagination metadata.
    Events are ordered by creation date (newest first).
    """
    async with get_db_session() as session:
        events, total = await _usage_repository.get_events_for_tenant(
            session=session,
            tenant_id=tenant_info.tenant_id,
            from_date=from_date,
            to_date=to_date,
            operation=operation,
            model=model,
            actor_type=actor_type,
            status=status,
            page=page,
            limit=limit,
        )

    return UsageEventsResponse(
        pagination=PaginationMeta(page=page, limit=limit, total=total),
        events=[UsageEventDTO.model_validate(e) for e in events],
    )


@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    tenant_info: TenantInfo = Depends(get_tenant_info),
    from_date: date = Query(
        ..., alias="from", description="Start of period (inclusive)"
    ),
    to_date: date = Query(..., alias="to", description="End of period (inclusive)"),
    operation: str | None = Query(None, description="Filter by operation"),
    model: str | None = Query(None, description="Filter by model"),
) -> UsageSummaryResponse:
    """Get aggregated usage summary for the authenticated tenant.

    Returns total tokens and cost, plus breakdowns by day and by operation.
    """
    async with get_db_session() as session:
        summary = await _usage_repository.get_summary_for_tenant(
            session=session,
            tenant_id=tenant_info.tenant_id,
            from_date=from_date,
            to_date=to_date,
            operation=operation,
            model=model,
        )

    return UsageSummaryResponse(
        period=UsageSummaryPeriod(from_date=from_date, to_date=to_date),
        total_tokens=summary["total_tokens"],
        total_cost_usd=summary["total_cost_usd"],
        by_day=[
            UsageSummaryByDay(
                date=d["date"],
                tokens=d["tokens"],
                cost_usd=d["cost_usd"],
            )
            for d in summary["by_day"]
        ],
        by_operation=[
            UsageSummaryByOperation(
                operation=op["operation"],
                tokens=op["tokens"],
                cost_usd=op["cost_usd"],
            )
            for op in summary["by_operation"]
        ],
    )
