from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditRepository:
    @staticmethod
    def create(db: Session, audit_log: AuditLog) -> AuditLog:
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log

    @staticmethod
    def list_latest(db: Session, limit: int = 200) -> list[AuditLog]:
        return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
