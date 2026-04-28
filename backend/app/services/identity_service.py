"""Servicio principal del gestor de identidades — dueño del ciclo de vida."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple


from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.activation_token import ActivationToken
from app.models.certificate import Certificate
from app.models.credential import Credential
from app.models.user import User
from app.repositories.activation_repository import ActivationRepository
from app.repositories.area_repository import AreaRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.crypto_service import CryptoService
from app.services.notification_service import NotificationService
from app.services.password_policy import PasswordPolicy
from app.utils.token_utils import hash_token

# Vigencia por defecto: 1 año
DEFAULT_EXPIRY_DAYS = 365


class IdentityService:
    # ------------------------------------------------------------------ #
    #  Alta de colaborador                                                 #
    # ------------------------------------------------------------------ #
    @staticmethod
    def create_collaborator(
        db: Session,
        actor_user_id: int,
        full_name: str,
        email: str,
        area_id: int,
        access_level_code: int,
        role_id: Optional[int],
        starts_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ) -> Tuple[User, Optional[str]]:
        existing = UserRepository.get_by_email(db, email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El correo ya existe")

        area = AreaRepository.get_by_id(db, area_id)
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área no encontrada")

        if role_id:
            role = RoleRepository.get_by_id(db, role_id)
            if not role:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
            if role.access_level.code != access_level_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El rol no pertenece al nivel de acceso seleccionado",
                )
        else:
            role = RoleRepository.get_default_role_by_level_code(db, access_level_code)
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No existe rol por defecto para ese nivel",
                )

        # Calcular vigencia
        now = datetime.now(timezone.utc)
        if starts_at is None:
            starts_at = now
        if expires_at is None:
            expires_at = now + timedelta(days=DEFAULT_EXPIRY_DAYS)

        user = User(
            full_name=full_name,
            email=email.lower(),
            status="PENDING",
            is_active=False,
            area_id=area_id,
            access_level_id=role.access_level_id,
            role_id=role.id,
            created_by_id=actor_user_id,
            starts_at=starts_at,
            expires_at=expires_at,
        )
        user = UserRepository.create(db, user)

        # Emitir certificado interno automáticamente
        CryptoService.issue_certificate(db, user, expires_at, issued_by=actor_user_id)
        db.commit()
        db.refresh(user)

        ActivationRepository.revoke_user_tokens(db, user.id)

        raw_token = uuid4().hex + uuid4().hex
        token_expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.ACTIVATION_TOKEN_EXPIRE_HOURS)
        activation = ActivationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=token_expires_at,
            consumed_at=None,
            is_revoked=False,
        )
        ActivationRepository.create(db, activation)

        activation_link = f"{settings.ACTIVATION_URL_BASE}?token={raw_token}"
        sent_by_smtp = NotificationService.send_activation_link(full_name, user.email, activation_link)
        demo_link = None if sent_by_smtp else activation_link

        return user, demo_link

    # ------------------------------------------------------------------ #
    #  Activación de cuenta (antes en AuthService)                         #
    # ------------------------------------------------------------------ #
    @staticmethod
    def activate_account(db: Session, token: str, password: str) -> Optional[User]:
        """Consume token de activación y materializa la credencial local.

        Transición: PENDING → ACTIVE
        """
        token_hash_value = hash_token(token)
        activation = ActivationRepository.get_valid_by_hash(db, token_hash_value)
        if not activation:
            return None

        user = activation.user

        # Solo se puede activar si está PENDING
        if user.status != "PENDING":
            return None

        # Validar política de contraseñas
        is_valid, error_msg = PasswordPolicy.validate(password, email=user.email)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

        # Materializar credencial con password_hash en Credential (no en User)
        user.status = "ACTIVE"
        user.is_active = True

        activation.consumed_at = datetime.now(timezone.utc)

        db.add(user)
        db.add(activation)

        if user.credential:
            # Actualizar credencial existente
            user.credential.password_hash = get_password_hash(password)
            user.credential.password_updated_at = datetime.now(timezone.utc)
            db.add(user.credential)
        else:
            # Crear credencial nueva
            credential = Credential(
                user_id=user.id,
                username=user.email,
                identity_provider="local",
                password_hash=get_password_hash(password),
                password_updated_at=datetime.now(timezone.utc),
            )
            db.add(credential)

        # Asegurarse de que el certificado esté VALID
        cert = user.active_certificate
        if not cert:
            # Re-emitir si no hay uno válido
            CryptoService.issue_certificate(
                db, user,
                user.expires_at or datetime.now(timezone.utc) + timedelta(days=DEFAULT_EXPIRY_DAYS),
            )

        db.commit()
        db.refresh(user)
        return user

    # ------------------------------------------------------------------ #
    #  Cambio de nivel / rol                                               #
    # ------------------------------------------------------------------ #
    @staticmethod
    def change_user_level(
        db: Session,
        user: User,
        access_level_code: int,
        role_id: Optional[int],
        area_id: Optional[int],
    ) -> User:
        if role_id:
            role = RoleRepository.get_by_id(db, role_id)
            if not role:
                raise HTTPException(status_code=404, detail="Rol no encontrado")
            if role.access_level.code != access_level_code:
                raise HTTPException(status_code=400, detail="Rol no coincide con nivel")
        else:
            role = RoleRepository.get_default_role_by_level_code(db, access_level_code)
            if not role:
                raise HTTPException(status_code=400, detail="Sin rol por defecto para nivel")

        if area_id is not None:
            area = AreaRepository.get_by_id(db, area_id)
            if not area:
                raise HTTPException(status_code=404, detail="Área no encontrada")
            user.area_id = area.id

        user.access_level_id = role.access_level_id
        user.role_id = role.id

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # ------------------------------------------------------------------ #
    #  Desactivación                                                       #
    # ------------------------------------------------------------------ #
    @staticmethod
    def deactivate_user(db: Session, user: User) -> User:
        """Desactiva al usuario y revoca su certificado activo."""
        user.status = "INACTIVE"
        user.is_active = False

        cert = user.active_certificate
        if cert:
            CryptoService.revoke_certificate(db, cert)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # ------------------------------------------------------------------ #
    #  Reactivación                                                        #
    # ------------------------------------------------------------------ #
    @staticmethod
    def reactivate_user(db: Session, user: User, actor_user_id: Optional[int] = None) -> User:
        """Reactivar usuario, re-emitiendo certificado si es necesario.

        Transiciones válidas: INACTIVE → ACTIVE, REVOKED → ACTIVE
        """
        if user.status not in ("INACTIVE", "REVOKED"):
            raise HTTPException(
                status_code=400,
                detail=f"No se puede reactivar un usuario en estado {user.status}",
            )

        # Check credential exists (password_hash now lives in Credential)
        credential = user.credential
        if not credential or not credential.password_hash:
            raise HTTPException(
                status_code=400,
                detail="El usuario nunca completó su activación. Debe activarse primero.",
            )

        user.status = "ACTIVE"
        user.is_active = True

        # Re-emitir certificado si no hay uno válido
        if not user.active_certificate:
            expires_at = user.expires_at or datetime.now(timezone.utc) + timedelta(days=DEFAULT_EXPIRY_DAYS)
            CryptoService.reissue_certificate(db, user, expires_at, issued_by=actor_user_id)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # ------------------------------------------------------------------ #
    #  Revocación explícita                                                #
    # ------------------------------------------------------------------ #
    @staticmethod
    def revoke_user(db: Session, user: User) -> User:
        """Revoca la identidad del usuario (más severo que desactivar)."""
        user.status = "REVOKED"
        user.is_active = False

        cert = user.active_certificate
        if cert:
            CryptoService.revoke_certificate(db, cert)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # ------------------------------------------------------------------ #
    #  Vigencia (G1-B fix: reissue instead of in-place cert update)        #
    # ------------------------------------------------------------------ #
    @staticmethod
    def update_user_expiry(
        db: Session,
        user: User,
        starts_at: Optional[datetime],
        expires_at: datetime,
        actor_user_id: Optional[int] = None,
    ) -> Tuple[User, Optional["Certificate"]]:
        """Actualiza la fecha de expiración del usuario y reemite su certificado.

        Instead of patching cert.expires_at in-place (which desynchronizes
        fingerprint vs. cert_data), we revoke the old cert and issue a new one.
        Returns (user, new_certificate) so the caller can log the new fingerprint.
        """
        if starts_at is not None:
            user.starts_at = starts_at
        user.expires_at = expires_at

        new_cert = None
        if user.active_certificate:
            new_cert = CryptoService.reissue_certificate(db, user, expires_at, issued_by=actor_user_id)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user, new_cert

    # ------------------------------------------------------------------ #
    #  Reemisión de certificado                                            #
    # ------------------------------------------------------------------ #
    @staticmethod
    def reissue_user_certificate(
        db: Session,
        user: User,
        actor_user_id: Optional[int] = None,
    ):
        """Reemite el certificado interno del usuario."""
        expires_at = user.expires_at or datetime.now(timezone.utc) + timedelta(days=DEFAULT_EXPIRY_DAYS)
        cert = CryptoService.reissue_certificate(db, user, expires_at, issued_by=actor_user_id)
        db.commit()
        db.refresh(user)
        return cert
