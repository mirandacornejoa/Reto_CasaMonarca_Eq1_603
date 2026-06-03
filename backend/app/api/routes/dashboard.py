"""Ruta del dashboard — bandeja de trabajo por perfil."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_active_user
from app.models.arco_request import ArcoRequest
from app.models.deletion_request import DeletionRequest
from app.models.user import User
from app.services.arco_service import ArcoService
from app.services.deletion_request_service import DeletionRequestService
from app.services.record_service import RecordService

router = APIRouter()


@router.get("/")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Retorna bandeja de trabajo según el rol del usuario autenticado."""
    level_code = current_user.access_level.code if current_user.access_level else 99
    role_name = current_user.role.name if current_user.role else "unknown"
    area_name = current_user.area.name if current_user.area else None

    stats = RecordService.get_dashboard_stats(db, current_user)

    # Solicitudes de eliminación — solo admin
    pending_deletions = []
    if level_code == 1:
        del_reqs = DeletionRequestService.get_pending(db)
        for dr in del_reqs:
            pending_deletions.append({
                "id": dr.id,
                "record_id": dr.record_id,
                "record_folio": dr.record.folio if dr.record else None,
                "record_name": dr.record.name_or_alias if dr.record else None,
                "requested_by_name": dr.requested_by.full_name if dr.requested_by else None,
                "reason": dr.reason,
                "created_at": dr.created_at.isoformat() if dr.created_at else None,
            })

    # Solicitudes ARCO activas — solo admin
    pending_arco = []
    if level_code == 1:
        arco_reqs = ArcoService.list_for_user(db, current_user)
        for ar in arco_reqs:
            pending_arco.append({
                "id": ar.id,
                "request_type": ar.request_type,
                "status": ar.status,
                "record_id": ar.record_id,
                "record_folio": ar.record.folio if ar.record else None,
                "record_name": ar.record.name_or_alias if ar.record else None,
                "requested_by_name": ar.requested_by.full_name if ar.requested_by else None,
                "created_at": ar.created_at.isoformat() if ar.created_at else None,
            })

    # Notificaciones — resoluciones que afectan al usuario actual
    notifications = []
    if level_code in (2, 3):
        # 1. Solicitudes ARCO resueltas donde este usuario fue el solicitante
        arco_resolved = (
            db.query(ArcoRequest)
            .filter(
                ArcoRequest.requested_by_id == current_user.id,
                ArcoRequest.status.in_(["COMPLETED", "APPROVED", "REJECTED"]),
            )
            .order_by(ArcoRequest.resolved_at.desc())
            .limit(20)
            .all()
        )
        for ar in arco_resolved:
            resolver = None
            if ar.status in ("APPROVED", "REJECTED") and ar.assigned_admin_id:
                resolver = db.query(User).filter(User.id == ar.assigned_admin_id).first()
            elif ar.status == "COMPLETED" and ar.assigned_coordinator_id:
                resolver = db.query(User).filter(User.id == ar.assigned_coordinator_id).first()

            type_label = {
                "ACCESS": "Acceso", "RECTIFICATION": "Rectificación",
                "CANCELLATION": "Cancelación", "OPPOSITION": "Oposición",
            }.get(ar.request_type, ar.request_type)
            status_label = {
                "COMPLETED": "Completada", "APPROVED": "Aprobada", "REJECTED": "Rechazada",
            }.get(ar.status, ar.status)

            notifications.append({
                "kind": "arco",
                "id": ar.id,
                "folio": ar.folio or f"ARCO-{ar.id}",
                "type_label": type_label,
                "status": ar.status,
                "status_label": status_label,
                "record_folio": ar.record.folio if ar.record else None,
                "record_id": ar.record_id,
                "resolver_name": resolver.full_name if resolver else None,
                "resolution_notes": ar.resolution_notes,
                "resolved_at": ar.resolved_at.isoformat() if ar.resolved_at else None,
            })

        # 2. Peticiones de eliminación resueltas donde este usuario fue el solicitante (nivel 2)
        if level_code == 2:
            del_resolved = (
                db.query(DeletionRequest)
                .filter(
                    DeletionRequest.requested_by_id == current_user.id,
                    DeletionRequest.status.in_(["approved", "rejected"]),
                )
                .order_by(DeletionRequest.reviewed_at.desc())
                .limit(20)
                .all()
            )
            for dr in del_resolved:
                reviewer = db.query(User).filter(User.id == dr.reviewed_by_id).first() if dr.reviewed_by_id else None
                status_label = "Aprobada" if dr.status == "approved" else "Rechazada"
                notifications.append({
                    "kind": "deletion",
                    "id": dr.id,
                    "folio": dr.folio or f"DEL-{dr.id}",
                    "type_label": "Petición de eliminación",
                    "status": dr.status,
                    "status_label": status_label,
                    "record_folio": dr.record.folio if dr.record else None,
                    "record_id": dr.record_id,
                    "resolver_name": reviewer.full_name if reviewer else None,
                    "resolution_notes": dr.review_notes,
                    "resolved_at": dr.reviewed_at.isoformat() if dr.reviewed_at else None,
                })

        # Ordenar todo por fecha descendente
        notifications.sort(key=lambda x: x.get("resolved_at") or "", reverse=True)
        notifications = notifications[:20]

    return {
        "role": role_name,
        "level_code": level_code,
        "area_name": area_name,
        "pending_deletions": pending_deletions,
        "pending_arco": pending_arco,
        "notifications": notifications,
        **stats,
    }
