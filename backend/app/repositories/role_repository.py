from typing import Optional

from sqlalchemy.orm import Session

from app.models.access_level import AccessLevel
from app.models.permission import Permission
from app.models.role import Role


class RoleRepository:
    @staticmethod
    def get_by_id(db: Session, role_id: int) -> Optional[Role]:
        return db.query(Role).filter(Role.id == role_id).first()

    @staticmethod
    def list_roles(db: Session) -> list[Role]:
        return db.query(Role).order_by(Role.id.asc()).all()

    @staticmethod
    def list_permissions(db: Session) -> list[Permission]:
        return db.query(Permission).order_by(Permission.code.asc()).all()

    @staticmethod
    def list_levels(db: Session) -> list[AccessLevel]:
        return db.query(AccessLevel).order_by(AccessLevel.code.asc()).all()

    @staticmethod
    def get_default_role_by_level_code(db: Session, level_code: int) -> Optional[Role]:
        return (
            db.query(Role)
            .join(AccessLevel, Role.access_level_id == AccessLevel.id)
            .filter(AccessLevel.code == level_code)
            .order_by(Role.id.asc())
            .first()
        )
