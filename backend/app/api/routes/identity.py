from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.repositories.area_repository import AreaRepository
from app.schemas.users import AreaRead, UserCreateByAdminRequest, UserCreateByAdminResponse
from app.services.audit_service import AuditService
from app.services.identity_service import IdentityService
from app.api.routes.users import _to_user_read

router = APIRouter()


@router.post("/collaborators", response_model=UserCreateByAdminResponse)
def create_collaborator(
    payload: UserCreateByAdminRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    user, activation_link = IdentityService.create_collaborator(
        db=db,
        actor_user_id=admin.id,
        full_name=payload.full_name,
        email=payload.email,
        area_id=payload.area_id,
        access_level_code=payload.access_level_code,
        role_id=payload.role_id,
    )

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="identity.create_user",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail=f"Usuario creado con nivel {payload.access_level_code}",
        request=request,
    )

    return UserCreateByAdminResponse(
        user=_to_user_read(user),
        activation_link=activation_link,
        activation_expires_in_hours=settings.ACTIVATION_TOKEN_EXPIRE_HOURS,
    )


@router.get("/areas", response_model=List[AreaRead])
def list_areas(
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    return AreaRepository.list_active(db)
