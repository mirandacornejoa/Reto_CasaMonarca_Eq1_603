from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.credential import Credential
from app.models.user import User
from app.repositories.activation_repository import ActivationRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.utils.token_utils import hash_token


class AuthService:
    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        user = UserRepository.get_by_email(db, email)
        if not user:
            return None, "Credenciales inválidas"

        if not user.is_active or user.status != "ACTIVE" or not user.password_hash:
            return None, "La cuenta no está activa"

        if not verify_password(password, user.password_hash):
            return None, "Credenciales inválidas"

        if user.credential:
            user.credential.last_login_at = datetime.now(timezone.utc)
            db.add(user.credential)
            db.commit()

        return user, None

    @staticmethod
    def build_token(user: User) -> str:
        return create_access_token(
            subject=str(user.id),
            extra={
                "email": user.email,
                "role": user.role.name if user.role else "",
                "level": user.access_level.code if user.access_level else None,
            },
        )

    @staticmethod
    def activate_account(db: Session, token: str, password: str) -> Optional[User]:
        token_hash = hash_token(token)
        activation = ActivationRepository.get_valid_by_hash(db, token_hash)
        if not activation:
            return None

        user = activation.user
        user.password_hash = get_password_hash(password)
        user.status = "ACTIVE"
        user.is_active = True

        activation.consumed_at = datetime.now(timezone.utc)

        db.add(user)
        db.add(activation)

        if not user.credential:
            credential = Credential(user_id=user.id, username=user.email, identity_provider="local")
            db.add(credential)
        db.commit()
        db.refresh(user)
        return user
