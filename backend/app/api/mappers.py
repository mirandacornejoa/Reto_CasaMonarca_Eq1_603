"""Mappers compartidos — elimina acoplamiento entre módulos de rutas."""

import json
import os
from typing import Optional

from sqlalchemy.orm import Session

from app.models.area import Area
from app.models.deletion_request import DeletionRequest
from app.models.user import User
from app.schemas.records import RecordRead
from app.schemas.users import UserRead
from app.services.field_encryption_service import FieldEncryptionService


def _safe_decrypt(enc_value: Optional[str], plain_value: Optional[str]) -> Optional[str]:
    """Devuelve la versión descifrada si existe, si no cae al valor en claro heredado."""
    if enc_value and os.getenv("FIELD_ENCRYPTION_KEY", ""):
        try:
            return FieldEncryptionService.decrypt(enc_value)
        except Exception:
            pass
    return plain_value


def to_user_read(user: User) -> UserRead:
    """Convierte modelo User a schema UserRead."""
    cert = user.active_certificate or user.latest_certificate
    assigned_to_name = None
    if user.assigned_to_id and user.assigned_to:
        assigned_to_name = user.assigned_to.full_name
    return UserRead(
        id=user.id,
        matricula=getattr(user, "matricula", None),
        full_name=user.full_name,
        email=user.email,
        status=user.status,
        is_active=user.is_active,
        area_id=user.area_id,
        area_name=user.area.name if user.area else None,
        access_level_code=user.access_level.code,
        access_level_name=user.access_level.name,
        role_id=user.role.id,
        role_name=user.role.name,
        starts_at=user.starts_at,
        expires_at=user.expires_at,
        user_subtype=user.user_subtype,
        coordinator_area=user.coordinator_area,
        assigned_to_id=user.assigned_to_id,
        assigned_to_name=assigned_to_name,
        certificate_id=cert.id if cert else None,
        certificate_status=cert.status if cert else None,
        certificate_serial=cert.serial_number if cert else None,
        certificate_expires_at=cert.expires_at if cert else None,
        created_at=user.created_at,
    )


def to_record_read(record, db: Session) -> RecordRead:
    """Convierte modelo MigrantRecord a schema RecordRead."""
    area_name = None
    if record.area_id:
        area = db.query(Area).filter(Area.id == record.area_id).first()
        area_name = area.name if area else None

    created_by_name = None
    if record.created_by_id:
        creator = db.query(User).filter(User.id == record.created_by_id).first()
        created_by_name = creator.full_name if creator else None

    # Parse needs JSON
    needs = None
    if record.needs:
        try:
            needs = json.loads(record.needs)
        except (json.JSONDecodeError, TypeError):
            needs = None

    # Nombres de operador y coordinador asignados
    operator_name = None
    if record.assigned_operator_id:
        op = db.query(User).filter(User.id == record.assigned_operator_id).first()
        operator_name = op.full_name if op else None
    coordinator_name = None
    if record.assigned_coordinator_id:
        coord = db.query(User).filter(User.id == record.assigned_coordinator_id).first()
        coordinator_name = coord.full_name if coord else None

    # Petición de eliminación pendiente para este registro
    pending_del = (
        db.query(DeletionRequest)
        .filter(DeletionRequest.record_id == record.id, DeletionRequest.status == "pending")
        .first()
    )
    pending_deletion_folio = pending_del.folio if pending_del else None
    pending_deletion_by = pending_del.requested_by.full_name if pending_del and pending_del.requested_by else None

    return RecordRead(
        id=record.id,
        folio=record.folio,
        # Formulario real
        attention_date=record.attention_date,
        first_name=record.first_name,
        last_name_1=record.last_name_1,
        last_name_2=record.last_name_2,
        phone=record.phone,
        country_of_origin=record.country_of_origin,
        state_department=record.state_department,
        civil_status=record.civil_status,
        birth_date=record.birth_date,
        population_group=record.population_group,
        # Legacy
        name_or_alias=_safe_decrypt(record.name_or_alias_enc, record.name_or_alias),
        nationality=record.nationality,
        language=record.language,
        age_range=record.age_range,
        gender=record.gender,
        contact_info=_safe_decrypt(record.contact_info_enc, record.contact_info),
        needs=needs,
        registration_date=record.registration_date,
        observations=record.observations,
        area_id=record.area_id,
        area_name=area_name,
        status=record.status,
        template_id=record.template_id,
        sha256_hash=record.sha256_hash,
        # Workflow
        workflow_status=record.workflow_status,
        assigned_operator_id=record.assigned_operator_id,
        assigned_operator_name=operator_name,
        assigned_coordinator_id=record.assigned_coordinator_id,
        assigned_coordinator_name=coordinator_name,
        channeled_at=record.channeled_at,
        channel_notes=getattr(record, "channel_notes", None),
        reviewed_at=record.reviewed_at,
        # Anonimización ARCO
        is_anonymized=bool(record.is_anonymized),
        anonymized_at=record.anonymized_at,
        # Petición de eliminación
        pending_deletion_folio=pending_deletion_folio,
        pending_deletion_by=pending_deletion_by,
        # Autoría
        created_by_id=record.created_by_id,
        created_by_name=created_by_name,
        updated_by_id=record.updated_by_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
