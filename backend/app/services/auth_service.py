"""AuthService — login, JWT, sesión, 2FA exclusivamente TOTP. NO gestiona ciclo de vida de identidad."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, decode_token, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.crypto_service import CryptoService
from app.services.totp_service import TOTPService


class AuthService:
    # ------------------------------------------------------------------ #
    #  Autenticación de credenciales (paso 1)                              #
    # ------------------------------------------------------------------ #
    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """Valida credenciales. Retorna (user, None) o (None, error_msg)."""
        user = UserRepository.get_by_email(db, email)
        if not user:
            return None, "Credenciales inválidas"

        # Credencial local: password_hash vive en Credential
        credential = user.credential
        if not credential or not credential.password_hash:
            return None, "La cuenta no ha sido activada"

        # Verificar estados prohibidos
        if user.status in ("REVOKED",):
            return None, "La identidad ha sido revocada. Contacte al administrador."

        if user.status in ("INACTIVE",):
            return None, "La cuenta está inactiva. Contacte al administrador."

        if user.status == "PENDING":
            return None, "La cuenta aún no ha sido activada."

        if user.status == "EXPIRED":
            return None, "La cuenta ha expirado. Contacte al administrador."

        if not user.is_active or user.status != "ACTIVE":
            return None, "La cuenta no está activa"

        if not verify_password(password, credential.password_hash):
            return None, "Credenciales inválidas"

        # Verificar vigencia del usuario
        if user.expires_at:
            now = datetime.now(timezone.utc)
            exp = user.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now > exp:
                # Auto-marcar como expirado
                user.status = "EXPIRED"
                user.is_active = False
                db.add(user)
                db.commit()
                return None, "La cuenta ha expirado. Contacte al administrador."

        # Verificar estado del certificado
        cert = user.active_certificate
        if cert:
            is_valid, cert_msg = CryptoService.check_validity(cert)
            if not is_valid:
                return None, f"Certificado inválido: {cert_msg}"

        return user, None

    # ------------------------------------------------------------------ #
    #  2FA: TOTP exclusivo                                                 #
    # ------------------------------------------------------------------ #
    @staticmethod
    def needs_totp_enrollment(user: User) -> bool:
        """True si el usuario NO tiene TOTP enrolado y debe hacerlo."""
        return not TOTPService.is_enrolled(user)

    @staticmethod
    def verify_totp(db: Session, user_id: int, totp_code: str) -> Optional[User]:
        """Valida código TOTP. Retorna User si es válido, None si falla."""
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return None
        if not TOTPService.verify(user, totp_code):
            return None
        if user.credential:
            user.credential.last_login_at = datetime.now(timezone.utc)
            db.add(user.credential)
            db.commit()
        return user

    # ------------------------------------------------------------------ #
    #  JWT: token pre-2FA (acceso limitado)                                #
    # ------------------------------------------------------------------ #
    @staticmethod
    def build_pre2fa_token(user: User) -> str:
        """Genera JWT temporal con stage=pre_2fa. NO autoriza acceso a recursos."""
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.PRE2FA_TOKEN_EXPIRE_MINUTES)
        return create_access_token(
            subject=str(user.id),
            extra={
                "email": user.email,
                "stage": "pre_2fa",
                "exp": expire,
            },
        )

    # ------------------------------------------------------------------ #
    #  JWT: token final (acceso completo)                                  #
    # ------------------------------------------------------------------ #
    @staticmethod
    def build_token(user: User) -> str:
        """Genera JWT final con stage=authenticated."""
        return create_access_token(
            subject=str(user.id),
            extra={
                "email": user.email,
                "role": user.role.name if user.role else "",
                "level": user.access_level.code if user.access_level else None,
                "stage": "authenticated",
            },
        )
