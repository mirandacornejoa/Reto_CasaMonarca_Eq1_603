"""Seed inicial de niveles, permisos, roles, áreas y admin."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.access_level import AccessLevel
from app.models.area import Area
from app.models.credential import Credential
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


BASE_PERMISSIONS = [
    {
        "code": "scope.consult",
        "name": "Consultar información",
        "description": "Permite consultar información",
    },
    {
        "code": "scope.edit",
        "name": "Consultar y editar información",
        "description": "Permite consultar y editar información",
    },
    {
        "code": "scope.authorize",
        "name": "Consultar, editar y autorizar",
        "description": "Permite consultar, editar y autorizar información",
    },
    {
        "code": "scope.template_manage",
        "name": "Crear/modificar plantillas",
        "description": "Permite crear plantillas y nuevos documentos",
    },
    {
        "code": "identity.manage_users",
        "name": "Gestionar usuarios",
        "description": "Alta, cambio de niveles y activación/desactivación",
    },
]

BASE_LEVELS = [
    {"code": 1, "name": "Nivel 1 - Administradores del sistema", "description": "Administración total"},
    {"code": 2, "name": "Nivel 2 - Coordinadores de área", "description": "Gestión por área"},
    {"code": 3, "name": "Nivel 3 - Personal operativo", "description": "Operación interna"},
    {"code": 4, "name": "Nivel 4 - Personal externo", "description": "Consulta externa"},
]

BASE_AREAS = [
    {"name": "Administración", "description": "Área administrativa"},
    {"name": "Operaciones", "description": "Área operativa"},
]


def get_or_create_permission(db: Session, data: dict) -> Permission:
    permission = db.query(Permission).filter(Permission.code == data["code"]).first()
    if permission:
        return permission
    permission = Permission(**data)
    db.add(permission)
    db.flush()
    return permission


def get_or_create_level(db: Session, data: dict) -> AccessLevel:
    level = db.query(AccessLevel).filter(AccessLevel.code == data["code"]).first()
    if level:
        return level
    level = AccessLevel(**data)
    db.add(level)
    db.flush()
    return level


def get_or_create_area(db: Session, data: dict) -> Area:
    area = db.query(Area).filter(Area.name == data["name"]).first()
    if area:
        return area
    area = Area(**data)
    db.add(area)
    db.flush()
    return area


def get_or_create_role(
    db: Session,
    name: str,
    description: str,
    level: AccessLevel,
    permission_codes: list[str],
    area_scoped: bool,
) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    permissions = (
        db.query(Permission).filter(Permission.code.in_(permission_codes)).all() if permission_codes else []
    )
    if role:
        role.description = description
        role.access_level_id = level.id
        role.area_scoped = area_scoped
        role.permissions = permissions
        db.add(role)
        db.flush()
        return role

    role = Role(
        name=name,
        description=description,
        access_level_id=level.id,
        area_scoped=area_scoped,
        is_system=True,
    )
    role.permissions = permissions
    db.add(role)
    db.flush()
    return role


def seed() -> None:
    db = SessionLocal()
    try:
        for level_data in BASE_LEVELS:
            get_or_create_level(db, level_data)

        for area_data in BASE_AREAS:
            get_or_create_area(db, area_data)

        for permission_data in BASE_PERMISSIONS:
            get_or_create_permission(db, permission_data)

        db.flush()

        level_1 = db.query(AccessLevel).filter(AccessLevel.code == 1).first()
        level_2 = db.query(AccessLevel).filter(AccessLevel.code == 2).first()
        level_3 = db.query(AccessLevel).filter(AccessLevel.code == 3).first()
        level_4 = db.query(AccessLevel).filter(AccessLevel.code == 4).first()

        get_or_create_role(
            db,
            name="SYSTEM_ADMIN",
            description="Administrador del sistema",
            level=level_1,
            permission_codes=[
                "scope.consult",
                "scope.edit",
                "scope.authorize",
                "scope.template_manage",
                "identity.manage_users",
            ],
            area_scoped=False,
        )
        get_or_create_role(
            db,
            name="AREA_COORDINATOR",
            description="Coordinador de área",
            level=level_2,
            permission_codes=["scope.consult", "scope.edit", "scope.authorize"],
            area_scoped=True,
        )
        get_or_create_role(
            db,
            name="AREA_OPERATOR",
            description="Personal operativo",
            level=level_3,
            permission_codes=["scope.consult", "scope.edit"],
            area_scoped=True,
        )
        get_or_create_role(
            db,
            name="EXTERNAL_STAFF",
            description="Personal externo",
            level=level_4,
            permission_codes=["scope.consult"],
            area_scoped=False,
        )

        admin_role = db.query(Role).filter(Role.name == "SYSTEM_ADMIN").first()
        admin_area = db.query(Area).filter(Area.name == "Administración").first()

        admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL.lower()).first()
        if not admin:
            admin = User(
                full_name=settings.ADMIN_FULL_NAME,
                email=settings.ADMIN_EMAIL.lower(),
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                status="ACTIVE",
                is_active=True,
                area_id=admin_area.id,
                access_level_id=level_1.id,
                role_id=admin_role.id,
                created_by_id=None,
            )
            db.add(admin)
            db.flush()

            credential = Credential(
                user_id=admin.id,
                identity_provider="local",
                username=admin.email,
                password_updated_at=datetime.now(timezone.utc),
            )
            db.add(credential)

        db.commit()
        print("Seed completado correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
