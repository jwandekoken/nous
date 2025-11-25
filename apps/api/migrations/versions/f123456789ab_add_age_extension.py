"""add age extension

Revision ID: f123456789ab
Revises: e0b88fc02f98
Create Date: 2025-11-25 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f123456789ab"
down_revision: Union[str, Sequence[str], None] = "e0b88fc02f98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS age;")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS age;")
