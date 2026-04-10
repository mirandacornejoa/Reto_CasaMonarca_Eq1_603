from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.audit_repository import AuditRepository


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
        request: Optional[Request] = None,
    ) -> AuditLog:
        ip_address = request.client.host if request and request.client else None
        entry = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            result=result,
            detail=detail,
            ip_address=ip_address,
        )
        return AuditRepository.create(db, entry)
