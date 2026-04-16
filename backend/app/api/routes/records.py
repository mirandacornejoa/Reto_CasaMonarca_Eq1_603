"""Rutas de registros de migrantes — CRUD con RBAC por nivel.

Nivel 4 (externo) NO tiene acceso a registros internos sensibles.
Niveles 1-3 pueden crear y editar; niveles 1-2 pueden leer todos.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.mappers import to_record_read
from app.core.database import get_db
from app.core.deps import require_active_user, require_operator_or_above
from app.schemas.records import RecordCreate, RecordRead, RecordUpdate
from app.services.audit_service import AuditService
from app.services.record_service import RecordService

router = APIRouter()


def _require_internal_user(current_user=Depends(require_active_user)):
    """Bloquea acceso a nivel 4 (externo) a registros internos sensibles."""
    level_code = current_user.access_level.code if current_user.access_level else 99
    if level_code >= 4:
        raise HTTPException(
            status_code=403,
            detail="El personal externo no tiene acceso a registros internos de migrantes",
        )
    return current_user


@router.post("/", response_model=RecordRead, status_code=201)
def create_record(
    payload: RecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_operator_or_above),
):
    """Crear registro de migrante. Niveles 1-3 pueden crear."""
    record = RecordService.create_record(
        db=db,
        name_or_alias=payload.name_or_alias,
        actor_user_id=current_user.id,
        nationality=payload.nationality,
        language=payload.language,
        age_range=payload.age_range,
        gender=payload.gender,
        contact_info=payload.contact_info,
        needs=payload.needs,
        registration_date=payload.registration_date,
        observations=payload.observations,
        area_id=payload.area_id,
        status=payload.status,
        template_id=payload.template_id,
    )

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="records.create",
        resource="migrant_record",
        resource_id=str(record.id),
        result="SUCCESS",
        hash_related=record.sha256_hash,
        detail=f"Registro creado: {record.folio} - {record.name_or_alias}",
        request=request,
    )

    return to_record_read(record, db)


@router.get("/", response_model=List[RecordRead])
def list_records(
    area_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(_require_internal_user),
):
    """Listar registros. Niveles 1-3 tienen acceso. Nivel 4 bloqueado."""
    records = RecordService.list_records(
        db, area_id=area_id, status=status, search=search, limit=min(limit, 500),
    )
    return [to_record_read(r, db) for r in records]


@router.get("/{record_id}", response_model=RecordRead)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(_require_internal_user),
):
    """Detalle de un registro. Niveles 1-3."""
    record = RecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return to_record_read(record, db)


@router.patch("/{record_id}", response_model=RecordRead)
def update_record(
    record_id: int,
    payload: RecordUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_operator_or_above),
):
    """Editar registro. Niveles 1-3 pueden editar."""
    record = RecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    old_hash = record.sha256_hash

    record = RecordService.update_record(
        db=db,
        record=record,
        actor_user_id=current_user.id,
        name_or_alias=payload.name_or_alias,
        nationality=payload.nationality,
        language=payload.language,
        age_range=payload.age_range,
        gender=payload.gender,
        contact_info=payload.contact_info,
        needs=payload.needs,
        observations=payload.observations,
        area_id=payload.area_id,
        status=payload.status,
    )

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="records.update",
        resource="migrant_record",
        resource_id=str(record.id),
        result="SUCCESS",
        hash_related=record.sha256_hash,
        detail=f"Hash anterior: {old_hash} → Nuevo: {record.sha256_hash}",
        request=request,
    )

    return to_record_read(record, db)


@router.get("/{record_id}/hash")
def get_record_hash(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(_require_internal_user),
):
    """Consultar hash SHA-256 de un registro. Niveles 1-3 con audit."""
    record = RecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="records.hash_query",
        resource="migrant_record",
        resource_id=str(record.id),
        result="SUCCESS",
        hash_related=record.sha256_hash,
        detail=f"Consulta de hash para registro {record.folio}",
        request=request,
    )

    return {
        "record_id": record.id,
        "folio": record.folio,
        "sha256_hash": record.sha256_hash,
        "name_or_alias": record.name_or_alias,
    }
