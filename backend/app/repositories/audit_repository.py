from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.arco_request import ArcoRequest
from app.models.deletion_request import DeletionRequest
from app.models.migrant_record import MigrantRecord
from app.models.user import User


def _lookup_resource_folio(db: Session, resource: str, resource_id: Optional[str]) -> Optional[str]:
    """Resuelve el folio legible del recurso auditado."""
    if not resource_id:
        return None
    try:
        rid = int(resource_id)
    except (ValueError, TypeError):
        return None

    if resource in ("arco_request",):
        row = db.query(ArcoRequest.folio).filter(ArcoRequest.id == rid).first()
        return row[0] if row else None
    if resource in ("deletion_request",):
        row = db.query(DeletionRequest.folio).filter(DeletionRequest.id == rid).first()
        return row[0] if row else None
    if resource in ("migrant_record", "record"):
        row = db.query(MigrantRecord.folio).filter(MigrantRecord.id == rid).first()
        return row[0] if row else None
    return None


class AuditRepository:
    @staticmethod
    def create(db: Session, audit_log: AuditLog) -> AuditLog:
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log

    @staticmethod
    def list_latest(
        db: Session,
        limit: int = 200,
        matricula: Optional[str] = None,
    ) -> List[dict]:
        """Lista bitácora con nombre, matrícula, rol del actor y folio del recurso."""
        query = (
            db.query(AuditLog, User.full_name, User.matricula, User.role_id)
            .outerjoin(User, AuditLog.actor_user_id == User.id)
        )

        # Filtro por matrícula del actor
        if matricula:
            query = query.filter(User.matricula.ilike(f"%{matricula}%"))

        rows = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

        # Cache de actores para evitar N+1 en el role lookup
        actor_cache: dict = {}
        results = []
        for log, actor_name, actor_matricula, _ in rows:
            role_name = None
            if log.actor_user_id:
                if log.actor_user_id not in actor_cache:
                    actor = db.query(User).filter(User.id == log.actor_user_id).first()
                    actor_cache[log.actor_user_id] = actor.role.name if actor and actor.role else None
                role_name = actor_cache[log.actor_user_id]

            resource_folio = _lookup_resource_folio(db, log.resource, log.resource_id)

            results.append({
                "id": log.id,
                "folio": getattr(log, "folio", None),
                "actor_user_id": log.actor_user_id,
                "actor_name": actor_name,
                "actor_matricula": actor_matricula,
                "actor_role": role_name,
                "action": log.action,
                "resource": log.resource,
                "resource_id": log.resource_id,
                "resource_folio": resource_folio,
                "result": log.result,
                "detail": log.detail,
                "hash_related": log.hash_related,
                "certificate_id": log.certificate_id,
                "ip_address": log.ip_address,
                "created_at": log.created_at,
            })
        return results
