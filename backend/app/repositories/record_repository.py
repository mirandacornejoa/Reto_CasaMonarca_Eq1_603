from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.migrant_record import MigrantRecord


class RecordRepository:
    @staticmethod
    def create(db: Session, record: MigrantRecord) -> MigrantRecord:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_by_id(db: Session, record_id: int) -> Optional[MigrantRecord]:
        return db.query(MigrantRecord).filter(MigrantRecord.id == record_id).first()

    @staticmethod
    def list_all(
        db: Session,
        area_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 200,
    ) -> List[MigrantRecord]:
        query = db.query(MigrantRecord)
        if area_id is not None:
            query = query.filter(MigrantRecord.area_id == area_id)
        if status is not None:
            query = query.filter(MigrantRecord.status == status)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                MigrantRecord.name_or_alias.ilike(pattern)
                | MigrantRecord.folio.ilike(pattern)
                | MigrantRecord.nationality.ilike(pattern)
            )
        return query.order_by(MigrantRecord.created_at.desc()).limit(limit).all()

    @staticmethod
    def update(db: Session, record: MigrantRecord) -> MigrantRecord:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
