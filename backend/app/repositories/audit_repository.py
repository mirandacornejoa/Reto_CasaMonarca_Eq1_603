from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


class AuditRepository:
    @staticmethod
    def create(db: Session, audit_log: AuditLog) -> AuditLog:
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log

    @staticmethod
    def list_latest(db: Session, limit: int = 200) -> List[dict]:
        """List audit logs with actor name and role info."""
        rows = (
            db.query(AuditLog, User.full_name, User.role_id)
            .outerjoin(User, AuditLog.actor_user_id == User.id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
        results = []
        for log, actor_name, _ in rows:
            role_name = None
            if log.actor_user_id:
                actor = db.query(User).filter(User.id == log.actor_user_id).first()
                if actor and actor.role:
                    role_name = actor.role.name
            results.append({
                "id": log.id,
                "actor_user_id": log.actor_user_id,
                "actor_name": actor_name,
                "actor_role": role_name,
                "action": log.action,
                "resource": log.resource,
                "resource_id": log.resource_id,
                "result": log.result,
                "detail": log.detail,
                "hash_related": log.hash_related,
                "certificate_id": log.certificate_id,
                "ip_address": log.ip_address,
                "created_at": log.created_at,
            })
        return results
