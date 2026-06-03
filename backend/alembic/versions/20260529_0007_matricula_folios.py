"""Agrega matricula a users, folio a arco_requests y deletion_requests.

Revision ID: 0007_matricula_folios
Revises: 0006_channel_notes
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_matricula_folios"
down_revision = "0006_channel_notes"
branch_labels = None
depends_on = None


def _column_exists(table, column):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column in [c["name"] for c in insp.get_columns(table)]


def upgrade() -> None:
    if not _column_exists("users", "matricula"):
        op.add_column("users", sa.Column("matricula", sa.String(20), nullable=True))
    if not _column_exists("arco_requests", "folio"):
        op.add_column("arco_requests", sa.Column("folio", sa.String(30), nullable=True))
    if not _column_exists("deletion_requests", "folio"):
        op.add_column("deletion_requests", sa.Column("folio", sa.String(30), nullable=True))


def downgrade() -> None:
    if _column_exists("deletion_requests", "folio"):
        op.drop_column("deletion_requests", "folio")
    if _column_exists("arco_requests", "folio"):
        op.drop_column("arco_requests", "folio")
    if _column_exists("users", "matricula"):
        op.drop_column("users", "matricula")
