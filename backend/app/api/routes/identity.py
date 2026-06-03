"""Rutas unificadas del gestor de identidades — ciclo de vida completo."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.mappers import to_user_read
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.repositories.area_repository import AreaRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ActivateAccountRequest
from app.schemas.certificates import CertificateRead
from app.schemas.users import (
    AreaRead,
    UserAssignmentUpdateRequest,
    UserCreateByAdminRequest,
    UserCreateByAdminResponse,
    UserExpiryUpdateRequest,
    UserLevelUpdateRequest,
    UserRead,
)
from app.services.audit_service import AuditService
from app.services.identity_service import IdentityService

router = APIRouter()


# ------------------------------------------------------------------ #
#  Alta de colaborador                                                 #
# ------------------------------------------------------------------ #
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
        starts_at=payload.starts_at,
        expires_at=payload.expires_at,
        user_subtype=payload.user_subtype,
        coordinator_area=payload.coordinator_area,
        assigned_to_id=payload.assigned_to_id,
    )

    cert = user.active_certificate
    cert_id = cert.id if cert else None
    cert_fingerprint = cert.fingerprint if cert else None

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="identity.create_user",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail=f"Usuario creado con nivel {payload.access_level_code}",
        certificate_id=cert_id,
        hash_related=cert_fingerprint,
        request=request,
    )

    if cert_id:
        AuditService.log(
            db=db,
            actor_user_id=admin.id,
            action="certificates.issue",
            resource="certificate",
            resource_id=str(cert_id),
            result="SUCCESS",
            detail=f"Certificado emitido para usuario {user.id} ({user.email})",
            certificate_id=cert_id,
            hash_related=cert_fingerprint,
            request=request,
        )

    return UserCreateByAdminResponse(
        user=to_user_read(user),
        activation_link=activation_link,
        activation_expires_in_hours=settings.ACTIVATION_TOKEN_EXPIRE_HOURS,
    )


# ------------------------------------------------------------------ #
#  Activación de cuenta                                                #
# ------------------------------------------------------------------ #
@router.post("/activate", status_code=200)
def activate_account(
    payload: ActivateAccountRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = IdentityService.activate_account(db, payload.token, payload.password)
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


# ------------------------------------------------------------------ #
#  Listar usuarios                                                     #
# ------------------------------------------------------------------ #
@router.get("/users", response_model=List[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    users = UserRepository.list_all(db)
    return [to_user_read(u) for u in users]


# ------------------------------------------------------------------ #
#  Detalle de usuario                                                  #
# ------------------------------------------------------------------ #
@router.get("/users/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return to_user_read(user)


# ------------------------------------------------------------------ #
#  Cambiar nivel/rol                                                   #
# ------------------------------------------------------------------ #
@router.patch("/users/{user_id}/level", response_model=UserRead)
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

    old_level = user.access_level.code if user.access_level else None

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
        detail=f"Nivel {old_level} → {payload.access_level_code}",
        request=request,
    )
    return to_user_read(user)


# ------------------------------------------------------------------ #
#  Desactivar usuario (G1-C: solo desactivar, no reactivar)            #
# ------------------------------------------------------------------ #
@router.patch("/users/{user_id}/status", response_model=UserRead)
def deactivate_user_status(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Desactiva un usuario. Para reactivar usar PATCH .../reactivate."""
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user = IdentityService.deactivate_user(db, user)

    cert = user.active_certificate or user.latest_certificate
    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="identity.deactivate",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail="Desactivado",
        certificate_id=cert.id if cert else None,
        request=request,
    )

    return to_user_read(user)


# ------------------------------------------------------------------ #
#  Revocar identidad                                                   #
# ------------------------------------------------------------------ #
@router.patch("/users/{user_id}/revoke", response_model=UserRead)
def revoke_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user = IdentityService.revoke_user(db, user)

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="identity.revoke",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail="Identidad revocada",
        request=request,
    )
    return to_user_read(user)


# ------------------------------------------------------------------ #
#  Reactivar                                                           #
# ------------------------------------------------------------------ #
@router.patch("/users/{user_id}/reactivate", response_model=UserRead)
def reactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user = IdentityService.reactivate_user(db, user, actor_user_id=admin.id)

    cert = user.active_certificate
    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="identity.reactivate",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail="Usuario reactivado",
        certificate_id=cert.id if cert else None,
        request=request,
    )
    return to_user_read(user)


# ------------------------------------------------------------------ #
#  Actualizar vigencia (G1-B: reissue cert, log new fingerprint)       #
# ------------------------------------------------------------------ #
@router.patch("/users/{user_id}/expiry", response_model=UserRead)
def update_user_expiry(
    user_id: int,
    payload: UserExpiryUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    old_expires = str(user.expires_at) if user.expires_at else "sin definir"

    user, new_cert = IdentityService.update_user_expiry(
        db, user, payload.starts_at, payload.expires_at, actor_user_id=admin.id,
    )

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="identity.change_expiry",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail=f"Vigencia: {old_expires} → {payload.expires_at}",
        certificate_id=new_cert.id if new_cert else None,
        hash_related=new_cert.fingerprint if new_cert else None,
        request=request,
    )
    return to_user_read(user)


# ------------------------------------------------------------------ #
#  Certificado de un usuario                                           #
# ------------------------------------------------------------------ #
@router.get("/users/{user_id}/certificate", response_model=Optional[CertificateRead])
def get_user_certificate(
    user_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    cert = user.active_certificate or user.latest_certificate
    if not cert:
        raise HTTPException(status_code=404, detail="Sin certificado emitido")
    return cert


# ------------------------------------------------------------------ #
#  Reemitir certificado                                                #
# ------------------------------------------------------------------ #
@router.post("/users/{user_id}/certificate/reissue", response_model=CertificateRead)
def reissue_certificate(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    cert = IdentityService.reissue_user_certificate(db, user, actor_user_id=admin.id)

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="certificates.reissue",
        resource="certificate",
        resource_id=str(cert.id),
        result="SUCCESS",
        detail=f"Certificado re-emitido para usuario {user.id}",
        certificate_id=cert.id,
        hash_related=cert.fingerprint,
        request=request,
    )
    return cert


# ------------------------------------------------------------------ #
#  Actualizar asignación jerárquica                                    #
# ------------------------------------------------------------------ #
@router.patch("/users/{user_id}/assignment", response_model=UserRead)
def update_user_assignment(
    user_id: int,
    payload: UserAssignmentUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Admin actualiza el supervisor asignado a un usuario (voluntario → operativo, operativo → coordinador)."""
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    old_assigned = user.assigned_to_id
    user.assigned_to_id = payload.assigned_to_id
    db.add(user)
    db.commit()
    db.refresh(user)

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="identity.update_assignment",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail=f"Asignación: {old_assigned} → {payload.assigned_to_id}",
        request=request,
    )
    return to_user_read(user)


# ------------------------------------------------------------------ #
#  Áreas                                                               #
# ------------------------------------------------------------------ #
@router.get("/areas", response_model=List[AreaRead])
def list_areas(
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    return AreaRepository.list_active(db)


# ------------------------------------------------------------------ #
#  Listas jerárquicas (operadores, coordinadores)                      #
# ------------------------------------------------------------------ #
@router.get("/operators", response_model=List[UserRead])
def list_operators(
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Lista usuarios con nivel 3 (operativo) activos."""
    from app.models.access_level import AccessLevel
    users = (
        db.query(User)
        .join(AccessLevel)
        .filter(AccessLevel.code == 3, User.is_active.is_(True))
        .all()
    )
    return [to_user_read(u) for u in users]


@router.get("/coordinators", response_model=List[UserRead])
def list_coordinators(
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Lista usuarios con nivel 2 (coordinador) activos."""
    from app.models.access_level import AccessLevel
    users = (
        db.query(User)
        .join(AccessLevel)
        .filter(AccessLevel.code == 2, User.is_active.is_(True))
        .all()
    )
    return [to_user_read(u) for u in users]

