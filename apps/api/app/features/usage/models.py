"""Database models for usage tracking."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime as SADateTime
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.postgres.session import Base


class TokenUsageEvent(Base):
    """Append-only record for one provider call (LLM or embedding)."""

    __tablename__ = "token_usage_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        SADateTime(timezone=True), server_default=func.now()
    )

    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )

    actor_type: Mapped[str] = mapped_column(String(length=20), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    feature: Mapped[str] = mapped_column(String(length=50), nullable=False)
    operation: Mapped[str] = mapped_column(String(length=100), nullable=False)
    endpoint: Mapped[str | None] = mapped_column(String(length=255), nullable=True)

    provider: Mapped[str | None] = mapped_column(String(length=50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(length=100), nullable=True)

    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_chars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_chars: Mapped[int | None] = mapped_column(Integer, nullable=True)

    cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=8), nullable=True
    )

    status: Mapped[str] = mapped_column(String(length=20), nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(length=100), nullable=True)

    __table_args__ = (
        Index("ix_token_usage_events_tenant_id_created_at", "tenant_id", "created_at"),
        Index("ix_token_usage_events_request_id", "request_id"),
        Index("ix_token_usage_events_operation_created_at", "operation", "created_at"),
    )
