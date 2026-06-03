from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.arco_request import ArcoRequest


class ArcoRequestRepository:
    @staticmethod
    def create(db: Session, req: ArcoRequest) -> ArcoRequest:
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def get_by_id(db: Session, req_id: int) -> Optional[ArcoRequest]:
        return db.query(ArcoRequest).filter(ArcoRequest.id == req_id).first()

    @staticmethod
    def list_by_requester(db: Session, user_id: int) -> List[ArcoRequest]:
        return (
            db.query(ArcoRequest)
            .filter(ArcoRequest.requested_by_id == user_id)
            .order_by(ArcoRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def list_by_coordinator(db: Session, coordinator_id: int) -> List[ArcoRequest]:
        """Solicitudes donde el coordinador está involucrado: asignadas, creadas por él,
        o pendientes sin asignar. Incluye historial resuelto."""
        from sqlalchemy import or_
        return (
            db.query(ArcoRequest)
            .filter(
                or_(
                    ArcoRequest.assigned_coordinator_id == coordinator_id,
                    ArcoRequest.requested_by_id == coordinator_id,
                    # Pendientes sin coordinador asignado (para que pueda tomarlas)
                    ArcoRequest.assigned_coordinator_id.is_(None),
                ),
            )
            .order_by(ArcoRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def list_escalated(db: Session) -> List[ArcoRequest]:
        """Solicitudes de cancelación escaladas al admin."""
        return (
            db.query(ArcoRequest)
            .filter(
                ArcoRequest.request_type == "CANCELLATION",
                ArcoRequest.status == "ESCALATED",
            )
            .order_by(ArcoRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def list_all_active(db: Session) -> List[ArcoRequest]:
        """Todas las solicitudes en estados no terminales para el admin."""
        return (
            db.query(ArcoRequest)
            .filter(ArcoRequest.status.in_(["PENDING", "IN_REVIEW", "ESCALATED"]))
            .order_by(ArcoRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def list_all(db: Session, status: Optional[str] = None) -> List[ArcoRequest]:
        q = db.query(ArcoRequest)
        if status:
            q = q.filter(ArcoRequest.status == status)
        return q.order_by(ArcoRequest.created_at.desc()).all()

    @staticmethod
    def save(db: Session, req: ArcoRequest) -> ArcoRequest:
        db.add(req)
        db.commit()
        db.refresh(req)
        return req
