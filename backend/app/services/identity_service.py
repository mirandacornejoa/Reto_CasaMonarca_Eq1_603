from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.activation_token import ActivationToken
from app.models.user import User
from app.repositories.activation_repository import ActivationRepository
from app.repositories.area_repository import AreaRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService
from app.utils.token_utils import hash_token


class IdentityService:
    @staticmethod
    def create_collaborator(
        db: Session,
        actor_user_id: int,
        full_name: str,
        email: str,
        area_id: int,
        access_level_code: int,
        role_id: Optional[int],
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

        user = User(
            full_name=full_name,
            email=email.lower(),
            status="PENDING",
            is_active=False,
            area_id=area_id,
            access_level_id=role.access_level_id,
            role_id=role.id,
            created_by_id=actor_user_id,
        )
        user = UserRepository.create(db, user)

        ActivationRepository.revoke_user_tokens(db, user.id)

        raw_token = uuid4().hex + uuid4().hex
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.ACTIVATION_TOKEN_EXPIRE_HOURS)
        activation = ActivationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
            consumed_at=None,
            is_revoked=False,
        )
        ActivationRepository.create(db, activation)

        activation_link = f"{settings.ACTIVATION_URL_BASE}?token={raw_token}"
        sent_by_smtp = NotificationService.send_activation_link(full_name, user.email, activation_link)
        demo_link = None if sent_by_smtp else activation_link

        return user, demo_link

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

    @staticmethod
    def change_user_status(db: Session, user: User, enable: bool) -> User:
        if enable:
            if user.password_hash:
                user.status = "ACTIVE"
                user.is_active = True
            else:
                user.status = "PENDING"
                user.is_active = False
        else:
            user.status = "INACTIVE"
            user.is_active = False

        db.add(user)
        db.commit()
        db.refresh(user)
        return user
