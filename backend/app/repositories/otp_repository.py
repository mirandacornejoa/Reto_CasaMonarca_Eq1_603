from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.otp_token import OtpToken


class OtpRepository:
    @staticmethod
    def create(db: Session, otp: OtpToken) -> OtpToken:
        db.add(otp)
        db.flush()
        return otp

    @staticmethod
    def get_valid_by_user(db: Session, user_id: int, otp_hash: str) -> Optional[OtpToken]:
        """Busca un OTP válido (no consumido, no revocado, no expirado) para un usuario."""
        now = datetime.now(timezone.utc)
        return (
            db.query(OtpToken)
            .filter(
                OtpToken.user_id == user_id,
                OtpToken.otp_hash == otp_hash,
                OtpToken.is_revoked == False,  # noqa: E712
                OtpToken.consumed_at.is_(None),
                OtpToken.expires_at > now,
            )
            .first()
        )

    @staticmethod
    def revoke_user_otps(db: Session, user_id: int) -> int:
        """Revoca todos los OTPs pendientes del usuario."""
        count = (
            db.query(OtpToken)
            .filter(
                OtpToken.user_id == user_id,
                OtpToken.is_revoked == False,  # noqa: E712
                OtpToken.consumed_at.is_(None),
            )
            .update({"is_revoked": True})
        )
        db.flush()
        return count
