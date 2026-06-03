"""Rutas de registros de migrantes — CRUD con RBAC por nivel y workflow operativo.

Permisos por nivel:
  - Nivel 1 (admin):       CRUD completo + aprobar eliminación
  - Nivel 2 (coordinador): CRU + solicitar eliminación + cerrar
  - Nivel 3 (operativo):   CR + revisar + canalizar
  - Nivel 4 (externo):     C (crear — ve solo sus propios registros)
"""

import hashlib
import json
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.mappers import to_record_read
from app.core.database import get_db
from app.core.deps import require_active_user, require_admin
from app.schemas.records import ChannelRequest, RecordApprove, RecordCreate, RecordRead, RecordUpdate
from app.services.audit_service import AuditService
from app.services.record_service import RecordService
from app.services.signing_service import SigningService

router = APIRouter()


def _get_level(user) -> int:
    return user.access_level.code if user.access_level else 99


@router.post("/", response_model=RecordRead, status_code=201)
def create_record(
    payload: RecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Crear registro de migrante. Todos los niveles (1-4) pueden crear."""
    record = RecordService.create_record(
        db=db,
        actor_user_id=current_user.id,
        # Formulario real
        first_name=payload.first_name,
        last_name_1=payload.last_name_1,
        last_name_2=payload.last_name_2,
        attention_date=payload.attention_date,
        phone=payload.phone,
        country_of_origin=payload.country_of_origin,
        state_department=payload.state_department,
        civil_status=payload.civil_status,
        birth_date=payload.birth_date,
        population_group=payload.population_group,
        # Legacy
        name_or_alias=payload.name_or_alias,
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
    workflow_status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Listar registros filtrados por rol del usuario."""
    level = _get_level(current_user)

    if level == 1:
        # Admin: ve todo
        records = RecordService.list_records(
            db, area_id=area_id, status=status, search=search, limit=min(limit, 500),
        )
    elif level == 2:
        # Coordinador: solo ve registros canalizados a él
        records = RecordService.list_by_coordinator(db, current_user.id, workflow_status=workflow_status)
    elif level == 3:
        # Operativo: ve registros asignados a él
        records = RecordService.list_by_operator(db, current_user.id, workflow_status=workflow_status)
    else:
        # Nivel 4 (voluntario/externo): no puede listar registros
        return []

    # Filtrar por workflow_status si se pasa y no es nivel 2/3 (ya filtrado)
    if workflow_status and level in (1, 4):
        records = [r for r in records if r.workflow_status == workflow_status]

    # Filtrar por búsqueda para niveles 2-4
    if search and level > 1:
        pattern = search.lower()
        records = [r for r in records if (
            pattern in (r.name_or_alias or "").lower()
            or pattern in (r.folio or "").lower()
            or pattern in (r.nationality or "").lower()
            or pattern in (r.first_name or "").lower()
            or pattern in (r.last_name_1 or "").lower()
        )]

    return [to_record_read(r, db) for r in records[:min(limit, 500)]]


@router.get("/{record_id}", response_model=RecordRead)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Detalle de un registro."""
    record = RecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    level = _get_level(current_user)
    # Nivel 4 (voluntario/externo) no puede ver el detalle de registros
    if level >= 4:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    return to_record_read(record, db)


@router.patch("/{record_id}", response_model=RecordRead)
def update_record(
    record_id: int,
    payload: RecordUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Editar registro. Solo niveles 1-2 (admin y coordinador) pueden editar. Requiere firma."""
    level = _get_level(current_user)
    if level > 2:
        raise HTTPException(status_code=403, detail="Se requiere nivel coordinador o superior para editar registros")

    record = RecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    # Firma obligatoria para edición
    if not payload.content_hash or not payload.signature_b64:
        raise HTTPException(
            status_code=422,
            detail="Editar un registro requiere firma digital. Sube tu archivo .key y usa tu contraseña.",
        )
    canonical = _build_canonical({
        "action": "edit",
        "resource_id": record_id,
        "resource_type": "record_edit",
    })
    expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if expected_hash != payload.content_hash:
        raise HTTPException(status_code=400, detail="El contenido firmado no corresponde a esta operación.")
    is_valid, msg = SigningService.verify_signature(
        db, current_user, "record_edit", record_id, payload.content_hash, payload.signature_b64
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Firma rechazada: {msg}")

    old_hash = record.sha256_hash

    record = RecordService.update_record(
        db=db,
        record=record,
        actor_user_id=current_user.id,
        attention_date=payload.attention_date,
        first_name=payload.first_name,
        last_name_1=payload.last_name_1,
        last_name_2=payload.last_name_2,
        phone=payload.phone,
        country_of_origin=payload.country_of_origin,
        state_department=payload.state_department,
        civil_status=payload.civil_status,
        birth_date=payload.birth_date,
        population_group=payload.population_group,
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


@router.delete("/{record_id}", status_code=200)
def delete_record(
    record_id: int,
    request: Request,
    payload: Optional[RecordApprove] = Body(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Eliminar registro. Solo nivel 1 (admin) puede eliminar directamente. Requiere firma."""
    record = RecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    # Firma obligatoria para eliminación directa
    content_hash = payload.content_hash if payload else None
    signature_b64 = payload.signature_b64 if payload else None
    if not content_hash or not signature_b64:
        raise HTTPException(
            status_code=422,
            detail="Eliminar un registro requiere firma digital. Sube tu archivo .key y usa tu contraseña.",
        )
    canonical = _build_canonical({
        "action": "delete",
        "resource_id": record_id,
        "resource_type": "record_delete",
    })
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != content_hash:
        raise HTTPException(status_code=400, detail="El contenido firmado no corresponde a esta operación.")
    is_valid, msg = SigningService.verify_signature(
        db, current_user, "record_delete", record_id, content_hash, signature_b64
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Firma rechazada: {msg}")

    folio = record.folio
    name = record.name_or_alias
    record_hash = record.sha256_hash

    RecordService.delete_record(db, record)

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="records.delete",
        resource="migrant_record",
        resource_id=str(record_id),
        result="SUCCESS",
        hash_related=record_hash,
        detail=f"Registro eliminado: {folio} - {name}",
        request=request,
    )

    return {"message": f"Registro {folio} eliminado correctamente"}


# ── Workflow endpoints ──

def _build_canonical(data: dict) -> str:
    return json.dumps(dict(sorted(data.items())), separators=(',', ':'), ensure_ascii=False)


@router.put("/{record_id}/review", response_model=RecordRead)
def review_record(
    record_id: int,
    request: Request,
    payload: Optional[RecordApprove] = Body(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Aprobar/revisar registro. Nivel 3 no firma. Niveles 1-2 requieren firma digital."""
    level = _get_level(current_user)
    if level > 3:
        raise HTTPException(status_code=403, detail="Se requiere nivel operativo o superior")

    record = RecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    # Firma obligatoria para coordinadores y admin
    if level <= 2:
        content_hash = payload.content_hash if payload else None
        signature_b64 = payload.signature_b64 if payload else None
        if not content_hash or not signature_b64:
            raise HTTPException(
                status_code=422,
                detail="Esta acción requiere firma digital. Sube tu archivo .key y usa tu contraseña.",
            )
        canonical = _build_canonical({
            "action": "approve",
            "resource_id": record_id,
            "resource_type": "record_approval",
        })
        expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if expected_hash != content_hash:
            raise HTTPException(status_code=400, detail="El contenido firmado no corresponde a esta operación.")
        is_valid, msg = SigningService.verify_signature(
            db, current_user, "record_approval", record_id, content_hash, signature_b64
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Firma rechazada: {msg}")

    try:
        record = RecordService.review_record(db, record, current_user.id, actor_level=level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    signed_note = " (firmado digitalmente)" if level <= 2 else ""
    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="records.review",
        resource="migrant_record",
        resource_id=str(record.id),
        result="SUCCESS",
        detail=f"Registro {record.folio} aprobado{signed_note}",
        request=request,
    )

    return to_record_read(record, db)


@router.put("/{record_id}/channel", response_model=RecordRead)
def channel_record(
    record_id: int,
    payload: ChannelRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Operativo canaliza registro al coordinador. Solo nivel 3 (operativo)."""
    level = _get_level(current_user)
    if level != 3:
        raise HTTPException(status_code=403, detail="Solo el operativo puede canalizar registros")

    record = RecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    try:
        record = RecordService.channel_record(db, record, current_user.id, notes=payload.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="records.channel",
        resource="migrant_record",
        resource_id=str(record.id),
        result="SUCCESS",
        detail=f"Registro {record.folio} canalizado al coordinador",
        request=request,
    )

    return to_record_read(record, db)


@router.put("/{record_id}/close", response_model=RecordRead)
def close_record(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Coordinador cierra un registro. Niveles 1-2."""
    level = _get_level(current_user)
    if level > 2:
        raise HTTPException(status_code=403, detail="Se requiere nivel coordinador o superior")

    record = RecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    try:
        record = RecordService.close_record(db, record, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="records.close",
        resource="migrant_record",
        resource_id=str(record.id),
        result="SUCCESS",
        detail=f"Registro {record.folio} cerrado",
        request=request,
    )

    return to_record_read(record, db)


@router.get("/{record_id}/hash")
def get_record_hash(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Consultar hash SHA-256 de un registro. Niveles 1-3 con audit."""
    level = _get_level(current_user)
    if level >= 4:
        raise HTTPException(status_code=403, detail="Acceso denegado")

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
