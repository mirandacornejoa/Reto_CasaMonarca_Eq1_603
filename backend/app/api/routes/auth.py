"""Auth routes — login con TOTP obligatorio, /me, firma documental."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_pre2fa_user, require_active_user, require_admin
from app.core.security import decode_token
from app.models.document_signature import DocumentSignature
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    DemoActivationResponse,
    MeResponse,
    SigningCertEnrollRequest,
    SigningCertStatusResponse,
    SigningEnrollResponse,
    TOTPEnrollBeginResponse,
    TOTPEnrollConfirmRequest,
    TOTPStatusResponse,
    TokenResponse,
    TwoFactorChallengeResponse,
    VerifySignatureRequest,
    VerifySignatureResponse,
    Verify2FARequest,
)
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.notification_service import NotificationService
from app.services.signing_service import SigningService
from app.services.totp_service import TOTPService

router = APIRouter()


# ------------------------------------------------------------------ #
#  Login (paso 1 → TOTP challenge o enrolamiento obligatorio)          #
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

    # Credenciales OK → generar token pre-2FA
    session_token = AuthService.build_pre2fa_token(user)
    needs_enrollment = AuthService.needs_totp_enrollment(user)

    if needs_enrollment:
        detail_msg = "TOTP enrollment requerido"
    else:
        detail_msg = "TOTP requerido"

    AuditService.log(
        db=db,
        actor_user_id=user.id,
        action="auth.2fa_requested",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail=detail_msg,
        request=request,
    )

    response = TwoFactorChallengeResponse(
        requires_2fa=True,
        session_token=session_token,
        two_fa_type="totp",
        requires_totp_enrollment=needs_enrollment,
    )
    return response


# ------------------------------------------------------------------ #
#  Verificar TOTP (paso 2 → JWT final)                                 #
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

    # Solo verificar TOTP (único 2FA soportado)
    user = AuthService.verify_totp(db, user_id, payload.otp_code)
    if not user:
        AuditService.log(
            db=db,
            actor_user_id=user_id,
            action="auth.2fa_failure",
            resource="user",
            resource_id=str(user_id),
            result="FAILURE",
            detail="Código TOTP inválido",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código TOTP inválido. Verifica que la hora de tu dispositivo esté sincronizada.",
        )

    # TOTP válido → emitir JWT final
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
        detail="Login completado con TOTP",
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


# ================================================================== #
#  TOTP — enrolamiento y gestión                                       #
#  NOTA: begin/confirm usan get_pre2fa_user para permitir              #
#  enrolamiento durante primer login (antes de tener token completo)   #
# ================================================================== #

@router.get("/totp/status", response_model=TOTPStatusResponse)
def totp_status(current_user=Depends(require_active_user)):
    """Retorna si el usuario tiene TOTP enrolado."""
    cred = current_user.credential
    enrolled_at = None
    if cred and cred.totp_enrolled_at:
        enrolled_at = cred.totp_enrolled_at.isoformat()
    return TOTPStatusResponse(
        totp_enrolled=TOTPService.is_enrolled(current_user),
        totp_enrolled_at=enrolled_at,
    )


@router.post("/totp/enroll/begin", response_model=TOTPEnrollBeginResponse)
def totp_enroll_begin(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_pre2fa_user),
):
    """Genera secreto TOTP y QR. Acepta token pre_2fa para primer enrolamiento."""
    result = TOTPService.begin_enrollment(current_user)
    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="totp.enroll_begin",
        resource="user",
        resource_id=str(current_user.id),
        result="SUCCESS",
        request=request,
    )
    return TOTPEnrollBeginResponse(**result)


@router.post("/totp/enroll/confirm")
def totp_enroll_confirm(
    payload: TOTPEnrollConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_pre2fa_user),
):
    """Confirma el enrolamiento TOTP validando un código de la app. Acepta token pre_2fa."""
    ok = TOTPService.confirm_enrollment(db, current_user, payload.secret_plain, payload.totp_code)
    if not ok:
        AuditService.log(
            db=db,
            actor_user_id=current_user.id,
            action="totp.enroll_failure",
            resource="user",
            resource_id=str(current_user.id),
            result="FAILURE",
            detail="Código TOTP incorrecto al confirmar enrolamiento",
            request=request,
        )
        raise HTTPException(status_code=400, detail="Código TOTP incorrecto. Verifica la hora de tu dispositivo.")
    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="totp.enrolled",
        resource="user",
        resource_id=str(current_user.id),
        result="SUCCESS",
        request=request,
    )
    return {"message": "TOTP enrolado correctamente"}


@router.delete("/totp/revoke/{user_id}")
def totp_revoke(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Admin: revoca/resetea el TOTP de un usuario (pérdida de dispositivo)."""
    if current_user.access_level.code != 1 and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Sin permisos")

    target = UserRepository.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    TOTPService.revoke_totp(db, target)
    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="totp.revoked",
        resource="user",
        resource_id=str(user_id),
        result="SUCCESS",
        detail=f"TOTP revocado por usuario {current_user.id}",
        request=request,
    )
    return {"message": "TOTP revocado. El usuario deberá enrolarse de nuevo."}


# ================================================================== #
#  Firma documental — certificado de firma (Web Crypto)               #
# ================================================================== #

@router.get("/signing/status", response_model=SigningCertStatusResponse)
def signing_cert_status(current_user=Depends(require_active_user)):
    """Estado del certificado de firma del usuario autenticado."""
    for cert in current_user.certificates:
        if cert.cert_type == "SIGNING" and cert.status == "VALID":
            return SigningCertStatusResponse(
                has_signing_cert=True,
                cert_id=cert.id,
                serial_number=cert.serial_number,
                status=cert.status,
                issued_at=cert.issued_at.isoformat(),
                expires_at=cert.expires_at.isoformat(),
                fingerprint=cert.fingerprint,
            )
    return SigningCertStatusResponse(has_signing_cert=False)


@router.post("/signing/enroll", response_model=SigningEnrollResponse)
def signing_enroll(
    payload: SigningCertEnrollRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """
    Genera certificado de firma tipo SAT.

    Solo disponible para administradores y coordinadores (niveles 1-2).
    El backend genera el par de claves ECDSA P-256, emite un certificado
    X.509 autofirmado (.cer), y cifra la clave privada con la contraseña
    del usuario (.key). La clave privada NO se guarda en el backend.
    """
    level = current_user.access_level.code if current_user.access_level else 99
    if level > 2:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores y coordinadores pueden generar certificados de firma",
        )
    cert, cer_pem, key_pem = SigningService.generate_signing_certificate(
        db=db,
        user=current_user,
        key_password=payload.key_password,
        issued_by=current_user.id,
        years=payload.years,
    )
    db.commit()
    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="signing.enrolled",
        resource="certificate",
        resource_id=str(cert.id),
        result="SUCCESS",
        detail=f"Certificado de firma SAT generado: {cert.serial_number[:16]}...",
        request=request,
    )

    cert_status = SigningCertStatusResponse(
        has_signing_cert=True,
        cert_id=cert.id,
        serial_number=cert.serial_number,
        status=cert.status,
        issued_at=cert.issued_at.isoformat(),
        expires_at=cert.expires_at.isoformat(),
        fingerprint=cert.fingerprint,
    )

    return SigningEnrollResponse(
        certificate=cert_status,
        cer_pem=cer_pem,
        key_pem=key_pem,
    )


@router.get("/signing/certificate/download")
def download_signing_certificate(
    current_user=Depends(require_active_user),
):
    """
    Descarga el certificado público (.cer) del usuario autenticado.
    Solo retorna el certificado del usuario dueño — nunca de otro usuario.
    """
    cer_pem = SigningService.get_user_certificate_pem(current_user)
    if not cer_pem:
        raise HTTPException(status_code=404, detail="No tiene certificado de firma activo")
    return {"cer_pem": cer_pem}


@router.post("/signing/verify", response_model=VerifySignatureResponse)
def signing_verify(
    payload: VerifySignatureRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Verifica una firma ECDSA enviada desde el navegador y registra evidencia."""
    is_valid, message = SigningService.verify_signature(
        db=db,
        user=current_user,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        content_hash=payload.content_hash,
        signature_b64=payload.signature_b64,
    )
    db.commit()
    action = "signing.verified" if is_valid else "signing.verify_failed"
    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action=action,
        resource=payload.resource_type,
        resource_id=str(payload.resource_id),
        result="SUCCESS" if is_valid else "FAILURE",
        detail=message,
        request=request,
    )
    return VerifySignatureResponse(is_valid=is_valid, message=message)


@router.get("/signing/signatures/{resource_type}/{resource_id}")
def get_resource_signatures(
    resource_type: str,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Consulta las firmas de un recurso (document o migrant_record)."""
    sigs = (
        db.query(DocumentSignature)
        .filter(
            DocumentSignature.resource_type == resource_type,
            DocumentSignature.resource_id == resource_id,
        )
        .order_by(DocumentSignature.signed_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "signer_user_id": s.signer_user_id,
            "signer_name": s.signer.full_name if s.signer else None,
            "certificate_id": s.certificate_id,
            "content_hash": s.content_hash,
            "algorithm": s.algorithm,
            "signed_at": s.signed_at.isoformat() if s.signed_at else None,
            "last_verification_result": s.last_verification_result,
        }
        for s in sigs
    ]


@router.delete("/signing/revoke/{user_id}")
def signing_revoke(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Admin: revoca el certificado de firma de un usuario."""
    if current_user.access_level.code != 1:
        raise HTTPException(status_code=403, detail="Solo administradores")
    target = UserRepository.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    SigningService.revoke_signing_certificate(db, target, revoked_by=current_user.id)
    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="signing.revoked",
        resource="user",
        resource_id=str(user_id),
        result="SUCCESS",
        request=request,
    )
    return {"message": "Certificado de firma revocado."}
