from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.audit_repository import AuditRepository


def _generate_audit_folio(db: Session) -> str:
    """Genera folio único por evento de bitácora: BIT-NNNNN."""
    last = (
        db.query(AuditLog)
        .filter(AuditLog.folio.like("BIT-%"))
        .order_by(AuditLog.id.desc())
        .first()
    )
    if last and last.folio:
        try:
            seq = int(last.folio.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"BIT-{seq:05d}"


class AuditService:
    @staticmethod
    def log(
        db: Session,
        action: str,
        resource: str,
        result: str,
        actor_user_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        detail: Optional[str] = None,
        hash_related: Optional[str] = None,
        certificate_id: Optional[int] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        ip_address = request.client.host if request and request.client else None
        folio = _generate_audit_folio(db)
        entry = AuditLog(
            folio=folio,
            actor_user_id=actor_user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            result=result,
            detail=detail,
            hash_related=hash_related,
            certificate_id=certificate_id,
            ip_address=ip_address,
        )
        return AuditRepository.create(db, entry)
