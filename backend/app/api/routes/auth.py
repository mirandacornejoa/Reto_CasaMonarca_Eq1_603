"""Auth routes — login con 2FA, /me, demo endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_active_user, require_admin
from app.core.security import decode_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    DemoActivationResponse,
    MeResponse,
    TokenResponse,
    TwoFactorChallengeResponse,
    Verify2FARequest,
)
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.notification_service import NotificationService

router = APIRouter()


# ------------------------------------------------------------------ #
#  Login (paso 1 → 2FA challenge)                                      #
# ------------------------------------------------------------------ #
@router.post("/login")
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

    # Credenciales OK → enviar OTP para 2FA
    sent_by_smtp, demo_otp = AuthService.send_otp(db, user)
    session_token = AuthService.build_pre2fa_token(user)

    AuditService.log(
        db=db,
        actor_user_id=user.id,
        action="auth.2fa_requested",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail="OTP enviado" if sent_by_smtp else "OTP generado (modo demo)",
        request=request,
    )

    response = TwoFactorChallengeResponse(
        requires_2fa=True,
        session_token=session_token,
        demo_otp=demo_otp,
    )
    return response


# ------------------------------------------------------------------ #
#  Verificar OTP (paso 2 → JWT final)                                  #
# ------------------------------------------------------------------ #
@router.post("/verify-2fa", response_model=TokenResponse)
def verify_2fa(
    payload: Verify2FARequest,
    request: Request,
    db: Session = Depends(get_db),
):
    # Validar session_token (pre_2fa)
    try:
        token_payload = decode_token(payload.session_token)
        user_id = int(token_payload.get("sub"))
        stage = token_payload.get("stage")
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de sesión inválido")

    if stage != "pre_2fa":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no es de pre-autenticación",
        )

    # Verificar OTP
    user = AuthService.verify_otp(db, user_id, payload.otp_code)
    if not user:
        AuditService.log(
            db=db,
            actor_user_id=user_id,
            action="auth.2fa_failure",
            resource="user",
            resource_id=str(user_id),
            result="FAILURE",
            detail="Código OTP inválido o expirado",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código de verificación inválido o expirado",
        )

    # OTP válido → emitir JWT final
    token = AuthService.build_token(user)

    AuditService.log(
        db=db,
        actor_user_id=user.id,
        action="auth.2fa_success",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        request=request,
    )
    AuditService.log(
        db=db,
        actor_user_id=user.id,
        action="auth.login",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail="Login completado con 2FA",
        request=request,
    )

    return TokenResponse(access_token=token)


# ------------------------------------------------------------------ #
#  /me                                                                 #
# ------------------------------------------------------------------ #
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


# ------------------------------------------------------------------ #
#  Demo endpoints                                                      #
# ------------------------------------------------------------------ #
@router.get("/demo/activation-links", response_model=List[DemoActivationResponse])
def get_demo_activation_links(_: object = Depends(require_admin)):
    return NotificationService.get_demo_activation_links()
