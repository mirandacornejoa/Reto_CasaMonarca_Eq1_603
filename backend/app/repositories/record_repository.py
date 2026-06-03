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

    @staticmethod
    def get_by_operator(
        db: Session, operator_id: int, workflow_status: Optional[str] = None, limit: int = 200,
    ) -> List[MigrantRecord]:
        q = db.query(MigrantRecord).filter(MigrantRecord.assigned_operator_id == operator_id)
        if workflow_status:
            q = q.filter(MigrantRecord.workflow_status == workflow_status)
        return q.order_by(MigrantRecord.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_by_coordinator(
        db: Session, coordinator_id: int, workflow_status: Optional[str] = None, limit: int = 200,
    ) -> List[MigrantRecord]:
        q = db.query(MigrantRecord).filter(MigrantRecord.assigned_coordinator_id == coordinator_id)
        if workflow_status:
            q = q.filter(MigrantRecord.workflow_status == workflow_status)
        return q.order_by(MigrantRecord.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_by_creator(db: Session, creator_id: int, limit: int = 200) -> List[MigrantRecord]:
        return (
            db.query(MigrantRecord)
            .filter(MigrantRecord.created_by_id == creator_id)
            .order_by(MigrantRecord.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_pending_from_volunteers(db: Session, operator_id: int, limit: int = 200) -> list:
        """Registros pendientes, sin canalizar, creados por voluntarios del operativo."""
        from app.models.user import User
        vol_ids = [v.id for v in db.query(User.id).filter(User.assigned_to_id == operator_id).all()]
        if not vol_ids:
            return []
        return (
            db.query(MigrantRecord)
            .filter(
                MigrantRecord.created_by_id.in_(vol_ids),
                MigrantRecord.workflow_status == "pendiente",
                MigrantRecord.assigned_coordinator_id.is_(None),
            )
            .order_by(MigrantRecord.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_by_workflow_status(db: Session, **filters) -> dict:
        """Cuenta registros agrupados por workflow_status con filtros opcionales."""
        from sqlalchemy import func as sqlfunc
        q = db.query(MigrantRecord.workflow_status, sqlfunc.count(MigrantRecord.id))
        for col, val in filters.items():
            if val is not None:
                q = q.filter(getattr(MigrantRecord, col) == val)
        rows = q.group_by(MigrantRecord.workflow_status).all()
        return {status: count for status, count in rows}

