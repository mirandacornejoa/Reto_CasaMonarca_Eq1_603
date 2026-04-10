from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.activation_token import ActivationToken


class ActivationRepository:
    @staticmethod
    def create(db: Session, token: ActivationToken) -> ActivationToken:
        db.add(token)
        db.commit()
        db.refresh(token)
        return token

    @staticmethod
    def get_valid_by_hash(db: Session, token_hash: str) -> Optional[ActivationToken]:
        now = datetime.now(timezone.utc)
        return (
            db.query(ActivationToken)
            .filter(ActivationToken.token_hash == token_hash)
            .filter(ActivationToken.is_revoked.is_(False))
            .filter(ActivationToken.consumed_at.is_(None))
            .filter(ActivationToken.expires_at > now)
            .first()
        )

    @staticmethod
    def revoke_user_tokens(db: Session, user_id: int) -> None:
        db.query(ActivationToken).filter(
            ActivationToken.user_id == user_id,
            ActivationToken.consumed_at.is_(None),
            ActivationToken.is_revoked.is_(False),
        ).update({ActivationToken.is_revoked: True}, synchronize_session=False)
        db.commit()
