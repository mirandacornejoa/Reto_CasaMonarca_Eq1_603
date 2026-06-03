"""Repositorio de solicitudes de eliminación."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.deletion_request import DeletionRequest


class DeletionRequestRepository:
    @staticmethod
    def create(db: Session, deletion_request: DeletionRequest) -> DeletionRequest:
        db.add(deletion_request)
        db.flush()
        db.refresh(deletion_request)
        return deletion_request

    @staticmethod
    def get_by_id(db: Session, request_id: int) -> Optional[DeletionRequest]:
        return db.query(DeletionRequest).filter(DeletionRequest.id == request_id).first()

    @staticmethod
    def list_pending(db: Session) -> List[DeletionRequest]:
        return (
            db.query(DeletionRequest)
            .filter(DeletionRequest.status == "pending")
            .order_by(DeletionRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def list_all(db: Session, status: Optional[str] = None, limit: int = 200) -> List[DeletionRequest]:
        q = db.query(DeletionRequest)
        if status:
            q = q.filter(DeletionRequest.status == status)
        return q.order_by(DeletionRequest.created_at.desc()).limit(limit).all()

    @staticmethod
    def list_by_requester(db: Session, user_id: int) -> List[DeletionRequest]:
        return (
            db.query(DeletionRequest)
            .filter(DeletionRequest.requested_by_id == user_id)
            .order_by(DeletionRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def get_pending_for_record(db: Session, record_id: int) -> Optional[DeletionRequest]:
        return (
            db.query(DeletionRequest)
            .filter(DeletionRequest.record_id == record_id, DeletionRequest.status == "pending")
            .first()
        )
