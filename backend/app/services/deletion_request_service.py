"""Servicio de solicitudes de eliminación — flujo coordinador → administrador."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.deletion_request import DeletionRequest
from app.repositories.deletion_request_repository import DeletionRequestRepository
from app.services.record_service import RecordService


def _generate_del_folio(db: Session) -> str:
    """Genera folio único para solicitud de eliminación: DEL-YYYY-NNNN."""
    year = datetime.now(timezone.utc).year
    prefix = f"DEL-{year}-"
    last = (
        db.query(DeletionRequest)
        .filter(DeletionRequest.folio.like(f"{prefix}%"))
        .order_by(DeletionRequest.id.desc())
        .first()
    )
    if last and last.folio:
        try:
            seq = int(last.folio.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


class DeletionRequestService:
    @staticmethod
    def create_request(
        db: Session,
        record_id: int,
        requested_by_id: int,
        reason: str,
    ) -> DeletionRequest:
        """Coordinador solicita eliminación de un registro."""
        # Verificar que no hay solicitud pendiente para el mismo registro
        existing = DeletionRequestRepository.get_pending_for_record(db, record_id)
        if existing:
            raise ValueError("Ya existe una solicitud de eliminación pendiente para este registro")

        record = RecordService.get_by_id(db, record_id)
        if not record:
            raise ValueError("Registro no encontrado")

        deletion_request = DeletionRequest(
            record_id=record_id,
            requested_by_id=requested_by_id,
            reason=reason,
            status="pending",
        )
        deletion_request = DeletionRequestRepository.create(db, deletion_request)
        deletion_request.folio = _generate_del_folio(db)
        db.add(deletion_request)
        db.commit()
        db.refresh(deletion_request)
        return deletion_request

    @staticmethod
    def approve_request(
        db: Session,
        request_id: int,
        admin_id: int,
        notes: Optional[str] = None,
    ) -> DeletionRequest:
        """Administrador aprueba solicitud de eliminación."""
        req = DeletionRequestRepository.get_by_id(db, request_id)
        if not req:
            raise ValueError("Solicitud no encontrada")
        if req.status != "pending":
            raise ValueError("La solicitud ya fue procesada")

        req.status = "approved"
        req.reviewed_by_id = admin_id
        req.review_notes = notes
        req.reviewed_at = datetime.now(timezone.utc)
        db.add(req)

        # Eliminar el registro asociado
        record = RecordService.get_by_id(db, req.record_id)
        if record:
            RecordService.delete_record(db, record)

        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def reject_request(
        db: Session,
        request_id: int,
        admin_id: int,
        notes: Optional[str] = None,
    ) -> DeletionRequest:
        """Administrador rechaza solicitud de eliminación."""
        req = DeletionRequestRepository.get_by_id(db, request_id)
        if not req:
            raise ValueError("Solicitud no encontrada")
        if req.status != "pending":
            raise ValueError("La solicitud ya fue procesada")

        req.status = "rejected"
        req.reviewed_by_id = admin_id
        req.review_notes = notes
        req.reviewed_at = datetime.now(timezone.utc)
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def get_pending(db: Session) -> List[DeletionRequest]:
        return DeletionRequestRepository.list_pending(db)

    @staticmethod
    def get_all(db: Session, status: Optional[str] = None) -> List[DeletionRequest]:
        return DeletionRequestRepository.list_all(db, status=status)

    @staticmethod
    def get_by_requester(db: Session, user_id: int) -> List[DeletionRequest]:
        return DeletionRequestRepository.list_by_requester(db, user_id)

    @staticmethod
    def get_by_id(db: Session, request_id: int) -> Optional[DeletionRequest]:
        return DeletionRequestRepository.get_by_id(db, request_id)
