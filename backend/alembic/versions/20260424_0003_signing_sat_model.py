"""Add revoked_at to certificates for SAT model lifecycle.

Revision ID: 0003_signing_sat
Revises: 20260421_0002_totp_signing_encryption
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0003_signing_sat"
down_revision = "20260421_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("certificates", sa.Column("revoked_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("certificates", "revoked_at")
