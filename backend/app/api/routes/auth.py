from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_active_user, require_admin
from app.schemas.auth import ActivateAccountRequest, DemoActivationResponse, MeResponse, TokenResponse
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.notification_service import NotificationService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user, error = AuthService.authenticate(db, form_data.username, form_data.password)
    if error:
        AuditService.log(
            db=db,
            actor_user_id=None,
            action="auth.login",
            resource="user",
            resource_id=form_data.username,
            result="FAILURE",
            detail=error,
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

    token = AuthService.build_token(user)
    AuditService.log(
        db=db,
        actor_user_id=user.id,
        action="auth.login",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        request=request,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(current_user=Depends(require_active_user)):
    return MeResponse(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        status=current_user.status,
        is_active=current_user.is_active,
        area_id=current_user.area_id,
        area_name=current_user.area.name if current_user.area else None,
        access_level_code=current_user.access_level.code,
        access_level_name=current_user.access_level.name,
        role_id=current_user.role.id,
        role_name=current_user.role.name,
        permissions=current_user.role.permissions,
    )


@router.post("/activate", status_code=status.HTTP_200_OK)
def activate_account(
    payload: ActivateAccountRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = AuthService.activate_account(db, payload.token, payload.password)
    if not user:
        AuditService.log(
            db=db,
            action="identity.activate_account",
            resource="activation_token",
            result="FAILURE",
            detail="Token inválido o vencido",
            request=request,
        )
        raise HTTPException(status_code=400, detail="Token inválido o vencido")

    AuditService.log(
        db=db,
        actor_user_id=user.id,
        action="identity.activate_account",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        request=request,
    )
    return {"message": "Cuenta activada correctamente"}


@router.get("/demo/activation-links", response_model=List[DemoActivationResponse])
def get_demo_activation_links(_: object = Depends(require_admin)):
    return NotificationService.get_demo_activation_links()
