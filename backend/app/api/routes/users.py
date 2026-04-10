from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.repositories.user_repository import UserRepository
from app.schemas.users import UserLevelUpdateRequest, UserRead, UserStatusUpdateRequest
from app.services.audit_service import AuditService
from app.services.identity_service import IdentityService

router = APIRouter()


def _to_user_read(user) -> UserRead:
    return UserRead(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        status=user.status,
        is_active=user.is_active,
        area_id=user.area_id,
        area_name=user.area.name if user.area else None,
        access_level_code=user.access_level.code,
        access_level_name=user.access_level.name,
        role_id=user.role.id,
        role_name=user.role.name,
        created_at=user.created_at,
    )


@router.get("/", response_model=List[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    users = UserRepository.list_all(db)
    return [_to_user_read(user) for user in users]


@router.patch("/{user_id}/level", response_model=UserRead)
def update_user_level(
    user_id: int,
    payload: UserLevelUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user = IdentityService.change_user_level(
        db=db,
        user=user,
        access_level_code=payload.access_level_code,
        role_id=payload.role_id,
        area_id=payload.area_id,
    )

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="identity.change_level",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail=f"Nuevo nivel {payload.access_level_code}",
        request=request,
    )
    return _to_user_read(user)


@router.patch("/{user_id}/status", response_model=UserRead)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user = IdentityService.change_user_status(db, user, payload.is_active)

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="identity.change_status",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail="Reactivado" if payload.is_active else "Desactivado",
        request=request,
    )

    return _to_user_read(user)
