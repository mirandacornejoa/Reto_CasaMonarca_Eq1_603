"""Sistema operativo real: jerarquía de usuarios, formulario de ingreso, workflow y solicitudes de eliminación.

Revision ID: 0004_operational
Revises: 0003_signing_sat
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_operational"
down_revision = "0003_signing_sat"
branch_labels = None
depends_on = None


def _is_sqlite():
    """Detecta si el motor actual es SQLite."""
    return op.get_bind().dialect.name == "sqlite"


def _column_exists(table, column):
    """Verifica si una columna ya existe en la tabla (para idempotencia en SQLite)."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns(table)]
    return column in columns


def _table_exists(table):
    """Verifica si una tabla ya existe."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table in insp.get_table_names()


def _safe_add_column(table, column):
    """Agrega columna solo si no existe (idempotente para SQLite dirty state)."""
    if not _column_exists(table, column.name):
        op.add_column(table, column)


def upgrade() -> None:
    # ── Users: campos de jerarquía ──
    _safe_add_column("users", sa.Column("user_subtype", sa.String(30), nullable=True))
    _safe_add_column("users", sa.Column("coordinator_area", sa.String(30), nullable=True))
    _safe_add_column("users", sa.Column("assigned_to_id", sa.Integer(), nullable=True))
    if not _is_sqlite():
        op.create_foreign_key(
            "fk_users_assigned_to", "users", "users",
            ["assigned_to_id"], ["id"],
        )

    # ── MigrantRecords: campos del formulario real ──
    _safe_add_column("migrant_records", sa.Column("attention_date", sa.Date(), nullable=True))
    _safe_add_column("migrant_records", sa.Column("first_name", sa.String(100), nullable=True))
    _safe_add_column("migrant_records", sa.Column("last_name_1", sa.String(100), nullable=True))
    _safe_add_column("migrant_records", sa.Column("last_name_2", sa.String(100), nullable=True))
    _safe_add_column("migrant_records", sa.Column("phone", sa.String(30), nullable=True))
    _safe_add_column("migrant_records", sa.Column("country_of_origin", sa.String(100), nullable=True))
    _safe_add_column("migrant_records", sa.Column("state_department", sa.String(100), nullable=True))
    _safe_add_column("migrant_records", sa.Column("civil_status", sa.String(30), nullable=True))
    _safe_add_column("migrant_records", sa.Column("birth_date", sa.Date(), nullable=True))
    _safe_add_column("migrant_records", sa.Column("population_group", sa.String(60), nullable=True))

    # ── MigrantRecords: campos de workflow ──
    _safe_add_column("migrant_records", sa.Column("workflow_status", sa.String(20), nullable=False, server_default="pendiente"))
    _safe_add_column("migrant_records", sa.Column("assigned_operator_id", sa.Integer(), nullable=True))
    _safe_add_column("migrant_records", sa.Column("assigned_coordinator_id", sa.Integer(), nullable=True))
    _safe_add_column("migrant_records", sa.Column("channeled_at", sa.DateTime(), nullable=True))
    _safe_add_column("migrant_records", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    if not _is_sqlite():
        op.create_foreign_key(
            "fk_records_operator", "migrant_records", "users",
            ["assigned_operator_id"], ["id"],
        )
        op.create_foreign_key(
            "fk_records_coordinator", "migrant_records", "users",
            ["assigned_coordinator_id"], ["id"],
        )

    # Indexes (create_index is idempotent-safe on most backends but guard anyway)
    try:
        op.create_index("ix_migrant_records_operator", "migrant_records", ["assigned_operator_id"])
    except Exception:
        pass
    try:
        op.create_index("ix_migrant_records_coordinator", "migrant_records", ["assigned_coordinator_id"])
    except Exception:
        pass

    # ── Tabla de solicitudes de eliminación ──
    if not _table_exists("deletion_requests"):
        op.create_table(
            "deletion_requests",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("record_id", sa.Integer(), sa.ForeignKey("migrant_records.id"), nullable=False),
            sa.Column("requested_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("reviewed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("review_notes", sa.Text(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_deletion_requests_id", "deletion_requests", ["id"])


def downgrade() -> None:
    if _table_exists("deletion_requests"):
        op.drop_table("deletion_requests")

    try:
        op.drop_index("ix_migrant_records_coordinator", table_name="migrant_records")
    except Exception:
        pass
    try:
        op.drop_index("ix_migrant_records_operator", table_name="migrant_records")
    except Exception:
        pass
    if not _is_sqlite():
        op.drop_constraint("fk_records_coordinator", "migrant_records", type_="foreignkey")
        op.drop_constraint("fk_records_operator", "migrant_records", type_="foreignkey")

    for col in ["reviewed_at", "channeled_at", "assigned_coordinator_id",
                "assigned_operator_id", "workflow_status", "population_group",
                "birth_date", "civil_status", "state_department", "country_of_origin",
                "phone", "last_name_2", "last_name_1", "first_name", "attention_date"]:
        if _column_exists("migrant_records", col):
            op.drop_column("migrant_records", col)

    if not _is_sqlite():
        op.drop_constraint("fk_users_assigned_to", "users", type_="foreignkey")

    for col in ["assigned_to_id", "coordinator_area", "user_subtype"]:
        if _column_exists("users", col):
            op.drop_column("users", col)
