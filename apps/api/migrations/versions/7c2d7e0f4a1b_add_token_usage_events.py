"""add_token_usage_events

Revision ID: 7c2d7e0f4a1b
Revises: b425e9837ea8
Create Date: 2026-01-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c2d7e0f4a1b"
down_revision: Union[str, Sequence[str], None] = "b425e9837ea8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "token_usage_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("feature", sa.String(length=50), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("input_chars", sa.Integer(), nullable=True),
        sa.Column("output_chars", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_token_usage_events_tenant_id_created_at",
        "token_usage_events",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_token_usage_events_request_id",
        "token_usage_events",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_token_usage_events_operation_created_at",
        "token_usage_events",
        ["operation", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_token_usage_events_operation_created_at", table_name="token_usage_events"
    )
    op.drop_index("ix_token_usage_events_request_id", table_name="token_usage_events")
    op.drop_index(
        "ix_token_usage_events_tenant_id_created_at", table_name="token_usage_events"
    )
    op.drop_table("token_usage_events")
