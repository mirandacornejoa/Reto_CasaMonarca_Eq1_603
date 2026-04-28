"""Servicio de registros de migrantes — CRUD con hash SHA-256 y cifrado de campos sensibles."""

import json
import os
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.migrant_record import MigrantRecord
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
            "nationality": record.nationality,
            "language": record.language,
            "age_range": record.age_range,
            "gender": record.gender,
            "contact_info": record.contact_info,
            "needs": record.needs,
            "registration_date": str(record.registration_date),
            "observations": record.observations,
            "area_id": record.area_id,
            "status": record.status,
        }

    @staticmethod
    def create_record(
        db: Session,
        name_or_alias: str,
        actor_user_id: int,
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

        record = MigrantRecord(
            folio=folio,
            name_or_alias=name_or_alias,  # campo en claro (búsquedas)
            name_or_alias_enc=_encrypt_field(name_or_alias),  # versión cifrada
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
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )
        record = RecordRepository.create(db, record)

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
    def delete_record(db: Session, record: MigrantRecord) -> None:
        """Elimina un registro de la base de datos (hard delete)."""
        db.delete(record)
        db.commit()

