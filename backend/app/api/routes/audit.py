"""Rutas de bitácora/auditoría con RBAC por nivel."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_active_user
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogRead

router = APIRouter()


@router.get("/", response_model=List[AuditLogRead])
def list_audit_logs(
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Bitácora de auditoría.
    - Nivel 1 (Admin): bitácora completa
    - Nivel 2 (Coordinador): NO tiene acceso por defecto
    - Nivel 3 (Operador): NO tiene acceso
    - Nivel 4 (Externo): NO tiene acceso
    """
    level_code = current_user.access_level.code if current_user.access_level else 99

    if level_code > 1:
        raise HTTPException(
            status_code=403,
            detail="Acceso a bitácora restringido al administrador del sistema",
        )

    return AuditRepository.list_latest(db, limit=min(limit, 500))
