"""Agrega folio a audit_logs; backfill de folios en bitácora y matrículas en usuarios.

Revision ID: 0008_audit_folio_backfill
Revises: 0007_matricula_folios
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision = "0008_audit_folio_backfill"
down_revision = "0007_matricula_folios"
branch_labels = None
depends_on = None


def _column_exists(table, column):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column in [c["name"] for c in insp.get_columns(table)]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Columna folio en audit_logs
    if not _column_exists("audit_logs", "folio"):
        op.add_column("audit_logs", sa.Column("folio", sa.String(20), nullable=True))

    # 2. Backfill: matrículas para usuarios sin matrícula (orden por id)
    users_without = conn.execute(
        text("SELECT id FROM users WHERE matricula IS NULL ORDER BY id ASC")
    ).fetchall()
    for i, (user_id,) in enumerate(users_without, start=1):
        # Buscar el máximo secuencial ya asignado para no chocar
        max_row = conn.execute(
            text("SELECT matricula FROM users WHERE matricula LIKE 'CM-USR-%' ORDER BY id DESC LIMIT 1")
        ).fetchone()
        if max_row and max_row[0]:
            try:
                seq = int(max_row[0].split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        matricula = f"CM-USR-{seq:04d}"
        conn.execute(
            text("UPDATE users SET matricula = :m WHERE id = :id"),
            {"m": matricula, "id": user_id},
        )

    # 3. Backfill: folios para entradas de bitácora sin folio (orden por id)
    logs_without = conn.execute(
        text("SELECT id FROM audit_logs WHERE folio IS NULL ORDER BY id ASC")
    ).fetchall()
    for (log_id,) in logs_without:
        # Buscar el máximo secuencial ya asignado
        max_row = conn.execute(
            text("SELECT folio FROM audit_logs WHERE folio LIKE 'BIT-%' ORDER BY id DESC LIMIT 1")
        ).fetchone()
        if max_row and max_row[0]:
            try:
                seq = int(max_row[0].split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        folio = f"BIT-{seq:05d}"
        conn.execute(
            text("UPDATE audit_logs SET folio = :f WHERE id = :id"),
            {"f": folio, "id": log_id},
        )


def downgrade() -> None:
    if _column_exists("audit_logs", "folio"):
        op.drop_column("audit_logs", "folio")
    # Las matrículas no se revierten (son datos, no estructura)
