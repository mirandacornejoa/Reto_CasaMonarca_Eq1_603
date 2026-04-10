from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogRead

router = APIRouter()


@router.get("/", response_model=List[AuditLogRead])
def list_audit_logs(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    return AuditRepository.list_latest(db, limit=min(limit, 500))
