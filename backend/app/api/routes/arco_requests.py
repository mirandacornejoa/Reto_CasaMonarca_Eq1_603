"""Rutas del módulo ARCO — Acceso, Rectificación, Cancelación, Oposición.

Permisos:
  - Nivel 3 (operativo):    crear solicitudes, ver las propias
  - Nivel 2 (coordinador):  ver las asignadas, atender / escalar
  - Nivel 1 (admin):        ver las escaladas, aprobar / rechazar
"""

import hashlib
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_active_user
from app.models.user import User
from app.schemas.arco_request import (
    ArcoRequestAttend,
    ArcoRequestCreate,
    ArcoRequestEscalate,
    ArcoRequestRead,
    ArcoRequestReview,
)
from app.services.arco_service import ArcoService
from app.services.audit_service import AuditService
from app.services.signing_service import SigningService

router = APIRouter()


def _level(user: User) -> int:
    return user.access_level.code if user.access_level else 99


def _build_canonical(data: dict) -> str:
    """Construye contenido canónico igual que buildCanonicalContent() del frontend."""
    return json.dumps(dict(sorted(data.items())), separators=(',', ':'), ensure_ascii=False)


def _require_signature(db: Session, user: User, canonical_data: dict, content_hash: str | None, signature_b64: str | None, resource_type: str, resource_id: int) -> None:
    """Valida firma ECDSA para usuarios nivel ≤ 2. Lanza HTTPException si inválida."""
    if content_hash is None or signature_b64 is None:
        raise HTTPException(
            status_code=422,
            detail="Esta acción requiere firma digital. Sube tu archivo .key y usa tu contraseña.",
        )
    canonical = _build_canonical(canonical_data)
    expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if expected_hash != content_hash:
        raise HTTPException(status_code=400, detail="El contenido firmado no corresponde a esta operación.")
    is_valid, msg = SigningService.verify_signature(
        db, user, resource_type, resource_id, content_hash, signature_b64
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Firma rechazada: {msg}")


def _to_read(req) -> ArcoRequestRead:
    return ArcoRequestRead(
        id=req.id,
        folio=getattr(req, "folio", None),
        request_type=req.request_type,
        status=req.status,
        record_id=req.record_id,
        record_folio=req.record.folio if req.record else None,
        record_name=req.record.name_or_alias if req.record else None,
        requested_by_id=req.requested_by_id,
        requested_by_name=req.requested_by.full_name if req.requested_by else None,
        assigned_coordinator_id=req.assigned_coordinator_id,
        assigned_coordinator_name=req.assigned_coordinator.full_name if req.assigned_coordinator else None,
        assigned_admin_id=req.assigned_admin_id,
        assigned_admin_name=req.assigned_admin.full_name if req.assigned_admin else None,
        reason=req.reason,
        description=req.description,
        requested_changes_json=req.requested_changes_json,
        resolution_notes=req.resolution_notes,
        created_at=req.created_at,
        updated_at=req.updated_at,
        resolved_at=req.resolved_at,
    )


# ─────────────────────────────────────────────────────────────────
#  Crear solicitud ARCO (nivel 3)
# ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=ArcoRequestRead, status_code=201)
def create_arco_request(
    payload: ArcoRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Operativo o coordinador crea una solicitud ARCO desde un registro."""
    if _level(current_user) not in {2, 3}:
        raise HTTPException(status_code=403, detail="Solo coordinadores y operativos pueden crear solicitudes ARCO")

    try:
        req = ArcoService.create_request(
            db=db,
            record_id=payload.record_id,
            requested_by_id=current_user.id,
            request_type=payload.request_type,
            reason=payload.reason,
            description=payload.description,
            requested_changes_json=payload.requested_changes_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="arco.create",
        resource="arco_request",
        resource_id=str(req.id),
        result="SUCCESS",
        detail=f"ARCO {req.request_type} creada para registro {payload.record_id}",
        request=request,
    )
    return _to_read(req)


# ─────────────────────────────────────────────────────────────────
#  Listar solicitudes según rol
# ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ArcoRequestRead])
def list_arco_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    if _level(current_user) > 3:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    requests = ArcoService.list_for_user(db, current_user)
    return [_to_read(r) for r in requests]


# ─────────────────────────────────────────────────────────────────
#  Detalle
# ─────────────────────────────────────────────────────────────────

@router.get("/{req_id}", response_model=ArcoRequestRead)
def get_arco_request(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    req = ArcoService.get_by_id(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud ARCO no encontrada")

    level = _level(current_user)
    if level == 3 and req.requested_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if level == 2 and req.assigned_coordinator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if level > 3:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    return _to_read(req)


# ─────────────────────────────────────────────────────────────────
#  Coordinador: atender (ACCESS / OPPOSITION / RECTIFICATION)
# ─────────────────────────────────────────────────────────────────

@router.put("/{req_id}/attend", response_model=ArcoRequestRead)
def attend_arco_request(
    req_id: int,
    payload: ArcoRequestAttend,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Coordinador o admin atiende y cierra ACCESS / OPPOSITION / RECTIFICATION. Requiere firma."""
    if _level(current_user) > 2:
        raise HTTPException(status_code=403, detail="Se requiere nivel coordinador o superior")

    # Obtener req para incluir record_id en el contenido canónico
    req_obj = ArcoService.get_by_id(db, req_id)
    if not req_obj:
        raise HTTPException(status_code=404, detail="Solicitud ARCO no encontrada")

    _require_signature(
        db, current_user,
        canonical_data={
            "action": "attend",
            "record_id": req_obj.record_id,
            "resource_id": req_id,
            "resource_type": "arco_request",
        },
        content_hash=payload.content_hash,
        signature_b64=payload.signature_b64,
        resource_type="arco_request",
        resource_id=req_id,
    )

    try:
        req = ArcoService.attend_request(
            db=db,
            req_id=req_id,
            coordinator_id=current_user.id,
            resolution_notes=payload.resolution_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="arco.attend",
        resource="arco_request",
        resource_id=str(req.id),
        result="SUCCESS",
        detail=f"ARCO {req.request_type} atendida (firmada) por {current_user.full_name}",
        request=request,
    )
    return _to_read(req)


# ─────────────────────────────────────────────────────────────────
#  Coordinador: escalar CANCELLATION al admin
# ─────────────────────────────────────────────────────────────────

@router.put("/{req_id}/escalate", response_model=ArcoRequestRead)
def escalate_arco_request(
    req_id: int,
    payload: ArcoRequestEscalate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Coordinador escala solicitud CANCELLATION al admin. No requiere firma."""
    if _level(current_user) > 2:
        raise HTTPException(status_code=403, detail="Se requiere nivel coordinador o superior")

    try:
        req = ArcoService.escalate_cancellation(
            db=db,
            req_id=req_id,
            coordinator_id=current_user.id,
            notes=payload.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="arco.escalate",
        resource="arco_request",
        resource_id=str(req.id),
        result="SUCCESS",
        detail=f"ARCO CANCELLATION escalada al admin (id={req_id})",
        request=request,
    )
    return _to_read(req)


# ─────────────────────────────────────────────────────────────────
#  Admin: aprobar o rechazar CANCELLATION
# ─────────────────────────────────────────────────────────────────

@router.put("/{req_id}/review", response_model=ArcoRequestRead)
def review_cancellation(
    req_id: int,
    payload: ArcoRequestReview,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Admin aprueba o rechaza una solicitud CANCELLATION escalada. Requiere firma."""
    if _level(current_user) != 1:
        raise HTTPException(status_code=403, detail="Solo el administrador puede resolver cancelaciones ARCO")

    if payload.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="La acción debe ser 'approve' o 'reject'")

    req_obj = ArcoService.get_by_id(db, req_id)
    if not req_obj:
        raise HTTPException(status_code=404, detail="Solicitud ARCO no encontrada")

    _require_signature(
        db, current_user,
        canonical_data={
            "action": payload.action,
            "record_id": req_obj.record_id,
            "resource_id": req_id,
            "resource_type": "arco_request",
        },
        content_hash=payload.content_hash,
        signature_b64=payload.signature_b64,
        resource_type="arco_request",
        resource_id=req_id,
    )

    try:
        if payload.action == "approve":
            req = ArcoService.approve_cancellation(
                db=db,
                req_id=req_id,
                admin_id=current_user.id,
                resolution_notes=payload.resolution_notes,
            )
            action_label = "arco.approve_cancellation"
            detail = f"ARCO CANCELLATION aprobada y firmada — registro anonimizado (arco_id={req_id})"
        else:
            req = ArcoService.reject_cancellation(
                db=db,
                req_id=req_id,
                admin_id=current_user.id,
                resolution_notes=payload.resolution_notes,
            )
            action_label = "arco.reject_cancellation"
            detail = f"ARCO CANCELLATION rechazada y firmada (arco_id={req_id})"
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action=action_label,
        resource="arco_request",
        resource_id=str(req.id),
        result="SUCCESS",
        detail=detail,
        request=request,
    )
    return _to_read(req)
