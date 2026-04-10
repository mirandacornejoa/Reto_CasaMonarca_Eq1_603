from typing import Optional

from sqlalchemy.orm import Session

from app.models.area import Area


class AreaRepository:
    @staticmethod
    def get_by_id(db: Session, area_id: int) -> Optional[Area]:
        return db.query(Area).filter(Area.id == area_id).first()

    @staticmethod
    def list_active(db: Session) -> list[Area]:
        return db.query(Area).filter(Area.is_active.is_(True)).order_by(Area.name.asc()).all()
