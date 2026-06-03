"""Rutas de solicitudes de eliminación — flujo coordinador → administrador."""

import hashlib
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_active_user, require_admin
from app.models.user import User
from app.schemas.deletion_request import DeletionRequestCreate, DeletionRequestRead, DeletionRequestReview
from app.services.audit_service import AuditService
from app.services.deletion_request_service import DeletionRequestService
from app.services.signing_service import SigningService

router = APIRouter()


def _build_canonical(data: dict) -> str:
    return json.dumps(dict(sorted(data.items())), separators=(',', ':'), ensure_ascii=False)


def _to_read(req) -> dict:
    return {
        "id": req.id,
        "folio": getattr(req, "folio", None),
        "record_id": req.record_id,
        "record_folio": req.record.folio if req.record else None,
        "record_name": req.record.name_or_alias if req.record else None,
        "requested_by_id": req.requested_by_id,
        "requested_by_name": req.requested_by.full_name if req.requested_by else None,
        "reason": req.reason,
        "status": req.status,
        "reviewed_by_id": req.reviewed_by_id,
        "reviewed_by_name": req.reviewed_by.full_name if req.reviewed_by else None,
        "review_notes": req.review_notes,
        "reviewed_at": req.reviewed_at,
        "created_at": req.created_at,
    }


@router.post("/", response_model=DeletionRequestRead, status_code=201)
def create_deletion_request(
    payload: DeletionRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Crear solicitud de eliminación. Coordinadores (nivel 2) y superiores."""
    level_code = current_user.access_level.code if current_user.access_level else 99
    if level_code > 2:
        raise HTTPException(status_code=403, detail="Se requiere nivel coordinador o superior")

    try:
        req = DeletionRequestService.create_request(
            db=db,
            record_id=payload.record_id,
            requested_by_id=current_user.id,
            reason=payload.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="deletion_request.create",
        resource="deletion_request",
        resource_id=str(req.id),
        result="SUCCESS",
        detail=f"Solicitud de eliminación para registro {payload.record_id}: {payload.reason}",
        request=request,
    )

    return _to_read(req)


@router.get("/", response_model=List[DeletionRequestRead])
def list_deletion_requests(
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Listar solicitudes. Admin ve todas, coordinador ve las propias."""
    level_code = current_user.access_level.code if current_user.access_level else 99

    if level_code == 1:
        requests = DeletionRequestService.get_all(db, status=status)
    elif level_code <= 2:
        requests = DeletionRequestService.get_by_requester(db, current_user.id)
    else:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    return [_to_read(r) for r in requests]


@router.get("/{request_id}", response_model=DeletionRequestRead)
def get_deletion_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    req = DeletionRequestService.get_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    level_code = current_user.access_level.code if current_user.access_level else 99
    if level_code > 1 and req.requested_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    return _to_read(req)


@router.put("/{request_id}/review", response_model=DeletionRequestRead)
def review_deletion_request(
    request_id: int,
    payload: DeletionRequestReview,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Administrador aprueba o rechaza solicitud de eliminación. Requiere firma."""
    if payload.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Acción debe ser 'approve' o 'reject'")

    # Obtener la solicitud para el record_id canónico
    req_obj = DeletionRequestService.get_by_id(db, request_id)
    if not req_obj:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # Verificar firma
    if payload.content_hash is None or payload.signature_b64 is None:
        raise HTTPException(
            status_code=422,
            detail="Esta acción requiere firma digital. Sube tu archivo .key y usa tu contraseña.",
        )

    canonical = _build_canonical({
        "action": payload.action,
        "record_id": req_obj.record_id,
        "resource_id": request_id,
        "resource_type": "deletion_request",
    })
    expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if expected_hash != payload.content_hash:
        raise HTTPException(status_code=400, detail="El contenido firmado no corresponde a esta operación.")

    is_valid, msg = SigningService.verify_signature(
        db, admin, "deletion_request", request_id, payload.content_hash, payload.signature_b64
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Firma rechazada: {msg}")

    try:
        if payload.action == "approve":
            req = DeletionRequestService.approve_request(
                db=db, request_id=request_id, admin_id=admin.id, notes=payload.notes,
            )
        else:
            req = DeletionRequestService.reject_request(
                db=db, request_id=request_id, admin_id=admin.id, notes=payload.notes,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action=f"deletion_request.{payload.action}",
        resource="deletion_request",
        resource_id=str(request_id),
        result="SUCCESS",
        detail=f"Solicitud {payload.action} (firmada): {payload.notes or 'sin notas'}",
        request=request,
    )

    return _to_read(req)
