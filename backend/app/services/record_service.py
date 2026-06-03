"""Servicio de registros de migrantes — CRUD con hash SHA-256, cifrado de campos, y workflow operativo."""

import json
import os
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.migrant_record import MigrantRecord
from app.models.user import User
from app.repositories.record_repository import RecordRepository
from app.services.crypto_service import CryptoService
from app.services.field_encryption_service import FieldEncryptionService


def _encryption_enabled() -> bool:
    return bool(os.getenv("FIELD_ENCRYPTION_KEY", ""))


def _encrypt_field(value: Optional[str]) -> Optional[str]:
    if value is None or not _encryption_enabled():
        return value
    return FieldEncryptionService.encrypt(value)


def _decrypt_field(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not _encryption_enabled():
        return value
    return FieldEncryptionService.decrypt_or_none(value)


class RecordService:
    @staticmethod
    def _generate_folio(db: Session) -> str:
        """Genera un folio auto-incremental con formato CM-YYYY-NNNN."""
        year = datetime.now(timezone.utc).year
        prefix = f"CM-{year}-"
        last = (
            db.query(MigrantRecord)
            .filter(MigrantRecord.folio.like(f"{prefix}%"))
            .order_by(MigrantRecord.id.desc())
            .first()
        )
        if last and last.folio:
            try:
                seq = int(last.folio.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    @staticmethod
    def _hashable_dict(record: MigrantRecord) -> dict:
        """Construye diccionario con los campos relevantes para el hash."""
        return {
            "id": record.id,
            "folio": record.folio,
            "name_or_alias": record.name_or_alias,
            "first_name": record.first_name,
            "last_name_1": record.last_name_1,
            "last_name_2": record.last_name_2,
            "nationality": record.nationality,
            "language": record.language,
            "age_range": record.age_range,
            "gender": record.gender,
            "contact_info": record.contact_info,
            "phone": record.phone,
            "country_of_origin": record.country_of_origin,
            "civil_status": record.civil_status,
            "population_group": record.population_group,
            "needs": record.needs,
            "registration_date": str(record.registration_date),
            "observations": record.observations,
            "area_id": record.area_id,
            "status": record.status,
        }

    @staticmethod
    def _resolve_operator(db: Session, creator_user_id: int) -> Optional[int]:
        """Auto-asigna operativo basado en la cadena jerárquica del usuario creador."""
        user = db.query(User).filter(User.id == creator_user_id).first()
        if not user:
            return None
        level_code = user.access_level.code if user.access_level else 99
        # Si el creador es nivel 4 (externo/usuario), asignar a su operativo
        if level_code == 4 and user.assigned_to_id:
            return user.assigned_to_id
        # Si el creador es nivel 3 (operativo), se asigna a sí mismo
        if level_code == 3:
            return user.id
        # Si es coordinador o admin, no auto-asignar operativo
        return None

    @staticmethod
    def create_record(
        db: Session,
        actor_user_id: int,
        # Campos del formulario real
        first_name: Optional[str] = None,
        last_name_1: Optional[str] = None,
        last_name_2: Optional[str] = "X",
        attention_date: Optional[date] = None,
        phone: Optional[str] = None,
        country_of_origin: Optional[str] = None,
        state_department: Optional[str] = None,
        civil_status: Optional[str] = None,
        birth_date: Optional[date] = None,
        population_group: Optional[str] = None,
        # Campos legacy
        name_or_alias: Optional[str] = None,
        nationality: Optional[str] = None,
        language: Optional[str] = None,
        age_range: Optional[str] = None,
        gender: Optional[str] = None,
        contact_info: Optional[str] = None,
        needs: Optional[List[str]] = None,
        registration_date: Optional[datetime] = None,
        observations: Optional[str] = None,
        area_id: Optional[int] = None,
        status: str = "REGISTRADO",
        template_id: Optional[int] = None,
    ) -> MigrantRecord:
        folio = RecordService._generate_folio(db)
        needs_json = json.dumps(needs, ensure_ascii=False) if needs else None

        # Auto-componer name_or_alias desde campos del formulario real
        if first_name and last_name_1:
            composed_name = f"{first_name} {last_name_1}"
            if last_name_2 and last_name_2 != "X":
                composed_name += f" {last_name_2}"
            if not name_or_alias:
                name_or_alias = composed_name
        if not name_or_alias:
            name_or_alias = "Sin nombre"

        # Auto-mapear nationality desde country_of_origin si no viene
        if country_of_origin and not nationality:
            nationality = country_of_origin

        # Auto-mapear contact_info desde phone si no viene
        if phone and not contact_info:
            contact_info = phone

        # Auto-asignar operativo
        operator_id = RecordService._resolve_operator(db, actor_user_id)

        record = MigrantRecord(
            folio=folio,
            # Formulario real
            attention_date=attention_date,
            first_name=first_name,
            last_name_1=last_name_1,
            last_name_2=last_name_2,
            phone=phone,
            country_of_origin=country_of_origin,
            state_department=state_department,
            civil_status=civil_status,
            birth_date=birth_date,
            population_group=population_group,
            # Legacy
            name_or_alias=name_or_alias,
            name_or_alias_enc=_encrypt_field(name_or_alias),
            nationality=nationality,
            language=language,
            age_range=age_range,
            gender=gender,
            contact_info=contact_info,
            contact_info_enc=_encrypt_field(contact_info),
            needs=needs_json,
            registration_date=registration_date or datetime.now(timezone.utc),
            observations=observations,
            area_id=area_id,
            status=status,
            template_id=template_id,
            # Workflow
            workflow_status="pendiente",
            assigned_operator_id=operator_id,
            # Autoría
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )
        record = RecordRepository.create(db, record)

        # Auto-aprobar registros creados por niveles 1-3 (admin, coordinador, operativo)
        actor = db.query(User).filter(User.id == actor_user_id).first()
        actor_level = actor.access_level.code if actor and actor.access_level else 99
        if actor_level <= 3:
            record.workflow_status = "revisado"
            record.reviewed_at = datetime.now(timezone.utc)
            # Coordinador: asignarse a sí mismo para que aparezca en su bandeja
            if actor_level == 2:
                record.assigned_coordinator_id = actor_user_id
            db.add(record)

        # Calcular hash sobre datos persistidos
        record.sha256_hash = CryptoService.compute_record_hash(
            RecordService._hashable_dict(record)
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def update_record(
        db: Session,
        record: MigrantRecord,
        actor_user_id: int,
        # Campos del formulario real
        attention_date: Optional[date] = None,
        first_name: Optional[str] = None,
        last_name_1: Optional[str] = None,
        last_name_2: Optional[str] = None,
        phone: Optional[str] = None,
        country_of_origin: Optional[str] = None,
        state_department: Optional[str] = None,
        civil_status: Optional[str] = None,
        birth_date: Optional[date] = None,
        population_group: Optional[str] = None,
        # Legacy
        name_or_alias: Optional[str] = None,
        nationality: Optional[str] = None,
        language: Optional[str] = None,
        age_range: Optional[str] = None,
        gender: Optional[str] = None,
        contact_info: Optional[str] = None,
        needs: Optional[List[str]] = None,
        observations: Optional[str] = None,
        area_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> MigrantRecord:
        # Campos del formulario real
        if attention_date is not None:
            record.attention_date = attention_date
        if first_name is not None:
            record.first_name = first_name
        if last_name_1 is not None:
            record.last_name_1 = last_name_1
        if last_name_2 is not None:
            record.last_name_2 = last_name_2
        if phone is not None:
            record.phone = phone
        if country_of_origin is not None:
            record.country_of_origin = country_of_origin
        if state_department is not None:
            record.state_department = state_department
        if civil_status is not None:
            record.civil_status = civil_status
        if birth_date is not None:
            record.birth_date = birth_date
        if population_group is not None:
            record.population_group = population_group

        # Recomponer name_or_alias si se actualizaron nombres
        if first_name is not None or last_name_1 is not None:
            fn = record.first_name or ""
            ln1 = record.last_name_1 or ""
            ln2 = record.last_name_2 or ""
            composed = f"{fn} {ln1}".strip()
            if ln2 and ln2 != "X":
                composed += f" {ln2}"
            record.name_or_alias = composed
            record.name_or_alias_enc = _encrypt_field(composed)

        # Legacy
        if name_or_alias is not None:
            record.name_or_alias = name_or_alias
            record.name_or_alias_enc = _encrypt_field(name_or_alias)
        if nationality is not None:
            record.nationality = nationality
        if language is not None:
            record.language = language
        if age_range is not None:
            record.age_range = age_range
        if gender is not None:
            record.gender = gender
        if contact_info is not None:
            record.contact_info = contact_info
            record.contact_info_enc = _encrypt_field(contact_info)
        if needs is not None:
            record.needs = json.dumps(needs, ensure_ascii=False)
        if observations is not None:
            record.observations = observations
        if area_id is not None:
            record.area_id = area_id
        if status is not None:
            record.status = status

        record.updated_by_id = actor_user_id

        # Recalcular hash
        record.sha256_hash = CryptoService.compute_record_hash(
            RecordService._hashable_dict(record)
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    # ── Workflow operativo ──

    @staticmethod
    def review_record(db: Session, record: MigrantRecord, actor_user_id: int, actor_level: int = 3) -> MigrantRecord:
        """Aprueba el registro (marca como revisado).

        Regla de ownership: si ya fue canalizado a un coordinador, solo ese
        coordinador (nivel 2) o el admin (nivel 1) pueden aprobarlo.
        """
        if record.workflow_status != "pendiente":
            raise ValueError(f"Solo se pueden aprobar registros pendientes (actual: {record.workflow_status})")
        if actor_level == 3 and record.assigned_coordinator_id is not None:
            raise ValueError("El registro ya fue canalizado al coordinador — solo él puede aprobarlo")
        record.workflow_status = "revisado"
        record.reviewed_at = datetime.now(timezone.utc)
        record.updated_by_id = actor_user_id
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def channel_record(
        db: Session,
        record: MigrantRecord,
        operator_user_id: int,
        notes: Optional[str] = None,
    ) -> MigrantRecord:
        """Operativo canaliza el registro al coordinador asignado."""
        operator = db.query(User).filter(User.id == operator_user_id).first()
        if not operator or not operator.assigned_to_id:
            raise ValueError("El operativo no tiene coordinador asignado")

        record.workflow_status = "pendiente"
        record.channeled_at = datetime.now(timezone.utc)
        record.assigned_coordinator_id = operator.assigned_to_id
        record.channel_notes = notes or None
        record.updated_by_id = operator_user_id
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def close_record(db: Session, record: MigrantRecord, coordinator_user_id: int) -> MigrantRecord:
        """Coordinador cierra el registro."""
        if record.workflow_status != "canalizado":
            raise ValueError(f"Solo se pueden cerrar registros canalizados (actual: {record.workflow_status})")
        record.workflow_status = "cerrado"
        record.status = "CERRADO"
        record.updated_by_id = coordinator_user_id
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    # ── CRUD base ──

    @staticmethod
    def get_by_id(db: Session, record_id: int) -> Optional[MigrantRecord]:
        return RecordRepository.get_by_id(db, record_id)

    @staticmethod
    def list_records(
        db: Session,
        area_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 200,
    ) -> List[MigrantRecord]:
        return RecordRepository.list_all(db, area_id=area_id, status=status, search=search, limit=limit)

    @staticmethod
    def list_by_operator(db: Session, operator_id: int, workflow_status: Optional[str] = None) -> List[MigrantRecord]:
        return RecordRepository.get_by_operator(db, operator_id, workflow_status=workflow_status)

    @staticmethod
    def list_by_coordinator(db: Session, coordinator_id: int, workflow_status: Optional[str] = None) -> List[MigrantRecord]:
        return RecordRepository.get_by_coordinator(db, coordinator_id, workflow_status=workflow_status)

    @staticmethod
    def list_by_creator(db: Session, creator_id: int) -> List[MigrantRecord]:
        return RecordRepository.get_by_creator(db, creator_id)

    @staticmethod
    def delete_record(db: Session, record: MigrantRecord) -> None:
        """Elimina un registro de la base de datos (hard delete)."""
        db.delete(record)
        db.commit()

    @staticmethod
    def _record_summary(r: MigrantRecord) -> dict:
        return {
            "id": r.id,
            "folio": r.folio,
            "name": r.name_or_alias,
            "first_name": r.first_name,
            "last_name_1": r.last_name_1,
            "workflow_status": r.workflow_status,
            "country_of_origin": r.country_of_origin or r.nationality,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "channeled_at": r.channeled_at.isoformat() if r.channeled_at else None,
            "assigned_coordinator_id": r.assigned_coordinator_id,
        }

    @staticmethod
    def get_dashboard_stats(db: Session, user: User) -> dict:
        """Retorna bandeja de trabajo para el dashboard según el rol."""
        level_code = user.access_level.code if user.access_level else 99

        if level_code == 1:  # Admin — resumen global + conteos
            counts = RecordRepository.count_by_workflow_status(db)
            return {
                "total_records": sum(counts.values()),
                "pending_records": counts.get("pendiente", 0),
                "reviewed_records": counts.get("revisado", 0),
            }

        if level_code == 2:  # Coordinador — registros canalizados a él, pendientes
            records = RecordRepository.get_by_coordinator(db, user.id, workflow_status="pendiente")
            return {
                "work_items": [RecordService._record_summary(r) for r in records],
            }

        if level_code == 3:  # Operativo — pendientes de sus voluntarios, sin canalizar
            records = RecordRepository.get_pending_from_volunteers(db, user.id)
            return {
                "work_items": [RecordService._record_summary(r) for r in records],
            }

        return {}

    @staticmethod
    def list_pending_from_volunteers(db: Session, operator_id: int) -> List[MigrantRecord]:
        return RecordRepository.get_pending_from_volunteers(db, operator_id)
