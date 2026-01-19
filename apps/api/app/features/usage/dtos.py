"""DTOs for Usage API endpoints."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# =============================================================================
# Events Endpoint DTOs
# =============================================================================


class UsageEventDTO(BaseModel):
    """Single usage event for the events list."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    operation: str
    model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost_usd: Decimal | None
    status: str


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    limit: int
    total: int


class UsageEventsResponse(BaseModel):
    """Response for GET /usage/events."""

    pagination: PaginationMeta
    events: list[UsageEventDTO]


# =============================================================================
# Summary Endpoint DTOs
# =============================================================================


class UsageSummaryPeriod(BaseModel):
    """Period for the summary."""

    from_date: date
    to_date: date


class UsageSummaryByDay(BaseModel):
    """Aggregated usage for a single day."""

    date: date
    tokens: int
    cost_usd: Decimal


class UsageSummaryByOperation(BaseModel):
    """Aggregated usage for a single operation."""

    operation: str
    tokens: int
    cost_usd: Decimal


class UsageSummaryResponse(BaseModel):
    """Response for GET /usage/summary."""

    period: UsageSummaryPeriod
    total_tokens: int
    total_cost_usd: Decimal
    by_day: list[UsageSummaryByDay]
    by_operation: list[UsageSummaryByOperation]
