"""Servicio de solicitudes ARCO — Acceso, Rectificación, Cancelación, Oposición.

Flujo por tipo:
  ACCESS / OPPOSITION  : PENDING → IN_REVIEW → COMPLETED
  RECTIFICATION        : PENDING → IN_REVIEW → COMPLETED (el coordinador puede editar el registro)
  CANCELLATION         : PENDING → IN_REVIEW → ESCALATED → APPROVED / REJECTED
                         Al aprobar: anonimización controlada del registro.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.arco_request import ArcoRequest
from app.models.migrant_record import MigrantRecord
from app.models.user import User
from app.repositories.arco_request_repository import ArcoRequestRepository


# Campos identificables que se anulan al anonimizar
_IDENTIFIABLE_FIELDS = [
    "first_name", "last_name_1", "last_name_2",
    "phone", "birth_date",
    "country_of_origin", "state_department",
    "nationality",
    "name_or_alias_enc", "contact_info", "contact_info_enc",
    "observations",
    "sha256_hash",
]


def _generate_arco_folio(db: Session) -> str:
    """Genera folio único para solicitud ARCO: ARCO-YYYY-NNNN."""
    year = datetime.now(timezone.utc).year
    prefix = f"ARCO-{year}-"
    last = (
        db.query(ArcoRequest)
        .filter(ArcoRequest.folio.like(f"{prefix}%"))
        .order_by(ArcoRequest.id.desc())
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


class ArcoService:

    # ─────────────────────────────────────────────────────────────────
    #  Creación
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def create_request(
        db: Session,
        record_id: int,
        requested_by_id: int,
        request_type: str,
        reason: str,
        description: Optional[str] = None,
        requested_changes_json: Optional[str] = None,
    ) -> ArcoRequest:
        if request_type not in {"ACCESS", "RECTIFICATION", "CANCELLATION", "OPPOSITION"}:
            raise ValueError(f"Tipo de solicitud inválido: {request_type}")

        # Verificar que no haya una solicitud ARCO activa para este registro
        existing = (
            db.query(ArcoRequest)
            .filter(
                ArcoRequest.record_id == record_id,
                ArcoRequest.status.in_(["PENDING", "IN_REVIEW", "ESCALATED"]),
            )
            .first()
        )
        if existing:
            raise ValueError(
                f"Ya existe una solicitud ARCO activa para este registro "
                f"({existing.folio or f'ID {existing.id}'}). "
                f"Espera a que se resuelva antes de crear una nueva."
            )

        # Auto-asignar coordinador del operativo
        operator = db.query(User).filter(User.id == requested_by_id).first()
        coordinator_id = operator.assigned_to_id if operator else None

        req = ArcoRequest(
            request_type=request_type,
            status="PENDING",
            record_id=record_id,
            requested_by_id=requested_by_id,
            assigned_coordinator_id=coordinator_id,
            reason=reason,
            description=description,
            requested_changes_json=requested_changes_json,
        )
        req = ArcoRequestRepository.create(db, req)
        req.folio = _generate_arco_folio(db)
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    # ─────────────────────────────────────────────────────────────────
    #  Transiciones del coordinador
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def take_for_review(db: Session, req_id: int, coordinator_id: int) -> ArcoRequest:
        """Coordinador toma la solicitud (PENDING → IN_REVIEW)."""
        req = ArcoService._get_or_raise(db, req_id)
        if req.status != "PENDING":
            raise ValueError(f"La solicitud ya está en estado {req.status}")
        req.status = "IN_REVIEW"
        req.assigned_coordinator_id = coordinator_id
        return ArcoRequestRepository.save(db, req)

    @staticmethod
    def attend_request(
        db: Session,
        req_id: int,
        coordinator_id: int,
        resolution_notes: Optional[str],
    ) -> ArcoRequest:
        """Coordinador atiende ACCESS / OPPOSITION / RECTIFICATION → COMPLETED."""
        req = ArcoService._get_or_raise(db, req_id)
        if req.request_type == "CANCELLATION":
            raise ValueError("La cancelación debe escalarse al admin, no atenderse directamente.")
        if req.status not in ("PENDING", "IN_REVIEW"):
            raise ValueError(f"No se puede atender en estado {req.status}")

        req.status = "COMPLETED"
        req.resolution_notes = resolution_notes
        req.resolved_at = datetime.now(timezone.utc)
        return ArcoRequestRepository.save(db, req)

    @staticmethod
    def escalate_cancellation(
        db: Session,
        req_id: int,
        coordinator_id: int,
        notes: Optional[str],
    ) -> ArcoRequest:
        """Coordinador escala una solicitud CANCELLATION al admin (→ ESCALATED)."""
        req = ArcoService._get_or_raise(db, req_id)
        if req.request_type != "CANCELLATION":
            raise ValueError("Solo solicitudes de CANCELACIÓN pueden escalarse al admin")
        if req.status not in ("PENDING", "IN_REVIEW"):
            raise ValueError(f"No se puede escalar en estado {req.status}")

        req.status = "ESCALATED"
        if notes:
            req.resolution_notes = notes
        return ArcoRequestRepository.save(db, req)

    # ─────────────────────────────────────────────────────────────────
    #  Transiciones del admin
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def approve_cancellation(
        db: Session,
        req_id: int,
        admin_id: int,
        resolution_notes: Optional[str],
    ) -> ArcoRequest:
        """Admin aprueba CANCELLATION: anonimiza el registro y marca como APPROVED."""
        req = ArcoService._get_or_raise(db, req_id)
        if req.request_type != "CANCELLATION":
            raise ValueError("Solo solicitudes de CANCELACIÓN pueden aprobarse aquí")
        if req.status != "ESCALATED":
            raise ValueError(f"La solicitud debe estar ESCALATED para aprobar (actual: {req.status})")

        # Anonimizar registro si aún existe
        if req.record_id:
            record = db.query(MigrantRecord).filter(MigrantRecord.id == req.record_id).first()
            if record and not record.is_anonymized:
                ArcoService._anonymize_record(db, record, admin_id)

        req.status = "APPROVED"
        req.assigned_admin_id = admin_id
        req.resolution_notes = resolution_notes
        req.resolved_at = datetime.now(timezone.utc)
        return ArcoRequestRepository.save(db, req)

    @staticmethod
    def reject_cancellation(
        db: Session,
        req_id: int,
        admin_id: int,
        resolution_notes: Optional[str],
    ) -> ArcoRequest:
        """Admin rechaza CANCELLATION (→ REJECTED)."""
        req = ArcoService._get_or_raise(db, req_id)
        if req.request_type != "CANCELLATION":
            raise ValueError("Solo solicitudes de CANCELACIÓN pueden rechazarse aquí")
        if req.status != "ESCALATED":
            raise ValueError(f"La solicitud debe estar ESCALATED para rechazar (actual: {req.status})")

        req.status = "REJECTED"
        req.assigned_admin_id = admin_id
        req.resolution_notes = resolution_notes
        req.resolved_at = datetime.now(timezone.utc)
        return ArcoRequestRepository.save(db, req)

    # ─────────────────────────────────────────────────────────────────
    #  Lecturas
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def list_for_user(db: Session, user: User) -> List[ArcoRequest]:
        level = user.access_level.code if user.access_level else 99
        if level == 1:
            return ArcoRequestRepository.list_all_active(db)
        if level == 2:
            return ArcoRequestRepository.list_by_coordinator(db, user.id)
        return ArcoRequestRepository.list_by_requester(db, user.id)

    @staticmethod
    def get_by_id(db: Session, req_id: int) -> Optional[ArcoRequest]:
        return ArcoRequestRepository.get_by_id(db, req_id)

    # ─────────────────────────────────────────────────────────────────
    #  Anonimización controlada
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _anonymize_record(db: Session, record: MigrantRecord, actor_id: int) -> None:
        """Elimina datos personales identificables del registro.

        Conserva: id, folio, attention_date, area_id, gender, age_range,
                  population_group, civil_status, needs (datos agregados),
                  workflow_status, timestamps, assigned_*_id (solo IDs, no nombres).
        Nulifica: todo lo que identifica a la persona física.
        """
        # Nombre en claro queda como placeholder no identificable
        record.name_or_alias = "[CANCELACIÓN ARCO]"
        # Anonimizar todos los campos identificables
        for field in _IDENTIFIABLE_FIELDS:
            setattr(record, field, None)
        # Marcar como anonimizado
        record.is_anonymized = True
        record.anonymized_at = datetime.now(timezone.utc)
        record.updated_by_id = actor_id
        db.add(record)
        db.flush()

    # ─────────────────────────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_or_raise(db: Session, req_id: int) -> ArcoRequest:
        req = ArcoRequestRepository.get_by_id(db, req_id)
        if not req:
            raise ValueError(f"Solicitud ARCO {req_id} no encontrada")
        return req
