"""Agrega channel_notes a migrant_records.

Revision ID: 0006_channel_notes
Revises: 0005_arco_module
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_channel_notes"
down_revision = "0005_arco_module"
branch_labels = None
depends_on = None


def _column_exists(table, column):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column in [c["name"] for c in insp.get_columns(table)]


def upgrade() -> None:
    if not _column_exists("migrant_records", "channel_notes"):
        op.add_column("migrant_records", sa.Column("channel_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    if _column_exists("migrant_records", "channel_notes"):
        op.drop_column("migrant_records", "channel_notes")
