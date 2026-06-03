"""Módulo ARCO: tabla arco_requests y campos de anonimización en migrant_records.

Revision ID: 0005_arco_module
Revises: 0004_operational
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_arco_module"
down_revision = "0004_operational"
branch_labels = None
depends_on = None


def _is_sqlite():
    return op.get_bind().dialect.name == "sqlite"


def _column_exists(table, column):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns(table)]
    return column in columns


def _table_exists(table):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table in insp.get_table_names()


def _safe_add_column(table, column):
    if not _column_exists(table, column.name):
        op.add_column(table, column)


def upgrade() -> None:
    # ── MigrantRecords: campos de anonimización ARCO ──
    _safe_add_column("migrant_records", sa.Column("is_anonymized", sa.Boolean(), nullable=False, server_default="0"))
    _safe_add_column("migrant_records", sa.Column("anonymized_at", sa.DateTime(), nullable=True))

    # ── Tabla arco_requests ──
    if not _table_exists("arco_requests"):
        op.create_table(
            "arco_requests",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("request_type", sa.String(20), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
            sa.Column("record_id", sa.Integer(), sa.ForeignKey("migrant_records.id", ondelete="SET NULL"), nullable=True),
            sa.Column("requested_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("assigned_coordinator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("assigned_admin_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("requested_changes_json", sa.Text(), nullable=True),
            sa.Column("resolution_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
        )
        try:
            op.create_index("ix_arco_requests_id", "arco_requests", ["id"])
        except Exception:
            pass
        try:
            op.create_index("ix_arco_requests_record", "arco_requests", ["record_id"])
        except Exception:
            pass
        try:
            op.create_index("ix_arco_requests_requester", "arco_requests", ["requested_by_id"])
        except Exception:
            pass


def downgrade() -> None:
    if _table_exists("arco_requests"):
        try:
            op.drop_index("ix_arco_requests_requester", table_name="arco_requests")
        except Exception:
            pass
        try:
            op.drop_index("ix_arco_requests_record", table_name="arco_requests")
        except Exception:
            pass
        try:
            op.drop_index("ix_arco_requests_id", table_name="arco_requests")
        except Exception:
            pass
        op.drop_table("arco_requests")

    for col in ["anonymized_at", "is_anonymized"]:
        if _column_exists("migrant_records", col):
            op.drop_column("migrant_records", col)
