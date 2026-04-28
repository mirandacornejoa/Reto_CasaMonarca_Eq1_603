"""totp, signing certificate, document_signatures table, field encryption columns

Revision ID: 20260421_0002
Revises: 20260410_0001
Create Date: 2026-04-21

Migración idempotente — compatible con BD ya creada via AUTO_CREATE_TABLES=true.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260421_0002"
down_revision: Union[str, None] = "20260410_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def _table_exists(conn, table: str) -> bool:
    result = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
        {"t": table},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # credentials: columnas TOTP
    # ------------------------------------------------------------------
    if not _column_exists(conn, "credentials", "totp_secret_enc"):
        op.add_column("credentials", sa.Column("totp_secret_enc", sa.String(512), nullable=True))
    if not _column_exists(conn, "credentials", "totp_enrolled"):
        op.add_column("credentials", sa.Column("totp_enrolled", sa.Boolean(), nullable=False, server_default=sa.false()))
    if not _column_exists(conn, "credentials", "totp_enrolled_at"):
        op.add_column("credentials", sa.Column("totp_enrolled_at", sa.DateTime(), nullable=True))

    # ------------------------------------------------------------------
    # certificates: columna cert_type
    # ------------------------------------------------------------------
    if not _column_exists(conn, "certificates", "cert_type"):
        op.add_column("certificates", sa.Column("cert_type", sa.String(20), nullable=False, server_default="IDENTITY"))

    # ------------------------------------------------------------------
    # document_signatures: nueva tabla
    # ------------------------------------------------------------------
    if not _table_exists(conn, "document_signatures"):
        op.create_table(
            "document_signatures",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("resource_type", sa.String(40), nullable=False),
            sa.Column("resource_id", sa.Integer(), nullable=False),
            sa.Column("signer_user_id", sa.Integer(), nullable=False),
            sa.Column("certificate_id", sa.Integer(), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("signature_b64", sa.Text(), nullable=False),
            sa.Column("algorithm", sa.String(40), nullable=False, server_default="ECDSA-P256-SHA256"),
            sa.Column("signed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("last_verification_result", sa.String(20), nullable=True),
            sa.Column("last_verified_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["signer_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["certificate_id"], ["certificates.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_document_signatures_resource_id", "document_signatures", ["resource_id"])
        op.create_index("ix_document_signatures_signer_user_id", "document_signatures", ["signer_user_id"])

    # ------------------------------------------------------------------
    # migrant_records: columnas cifradas
    # ------------------------------------------------------------------
    if not _column_exists(conn, "migrant_records", "contact_info_enc"):
        op.add_column("migrant_records", sa.Column("contact_info_enc", sa.Text(), nullable=True))
    if not _column_exists(conn, "migrant_records", "name_or_alias_enc"):
        op.add_column("migrant_records", sa.Column("name_or_alias_enc", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "migrant_records", "name_or_alias_enc"):
        op.drop_column("migrant_records", "name_or_alias_enc")
    if _column_exists(conn, "migrant_records", "contact_info_enc"):
        op.drop_column("migrant_records", "contact_info_enc")

    if _table_exists(conn, "document_signatures"):
        op.drop_index("ix_document_signatures_signer_user_id", table_name="document_signatures")
        op.drop_index("ix_document_signatures_resource_id", table_name="document_signatures")
        op.drop_table("document_signatures")

    if _column_exists(conn, "certificates", "cert_type"):
        op.drop_column("certificates", "cert_type")

    if _column_exists(conn, "credentials", "totp_enrolled_at"):
        op.drop_column("credentials", "totp_enrolled_at")
    if _column_exists(conn, "credentials", "totp_enrolled"):
        op.drop_column("credentials", "totp_enrolled")
    if _column_exists(conn, "credentials", "totp_secret_enc"):
        op.drop_column("credentials", "totp_secret_enc")
