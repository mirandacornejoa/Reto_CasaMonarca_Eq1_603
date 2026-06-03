"""Seed inicial de niveles, permisos, roles, áreas, usuarios base con certificados, registros y plantilla de ejemplo.

Esquema RBAC:
  - Nivel 1 (Admin):       CRUD completo
  - Nivel 2 (Coordinador): CRU (sin eliminar)
  - Nivel 3 (Operativo):   CR (sin editar ni eliminar)
  - Nivel 4 (Externo):     C (solo crear)

Usuarios base:
  - 2 administradores (producción + contingencia)
  - 5 coordinadores (uno por área)
  - 1 operativo base
  - 1 externo base (voluntario)
"""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.access_level import AccessLevel
from app.models.area import Area
from app.models.audit_log import AuditLog
from app.models.credential import Credential
from app.models.migrant_record import MigrantRecord
from app.models.permission import Permission
from app.models.role import Role
from app.models.template import Template
from app.models.user import User
from app.services.crypto_service import CryptoService


# ──────────────────────────────────────────────────────────────────
#  Datos base
# ──────────────────────────────────────────────────────────────────

BASE_PERMISSIONS = [
    {"code": "records.create", "name": "Crear registros", "description": "Permite crear registros de migrantes"},
    {"code": "records.read", "name": "Leer registros", "description": "Permite consultar registros de migrantes"},
    {"code": "records.edit", "name": "Editar registros", "description": "Permite editar registros de migrantes"},
    {"code": "records.delete", "name": "Eliminar registros", "description": "Permite eliminar registros de migrantes"},
    {"code": "records.channel", "name": "Canalizar registros", "description": "Permite canalizar registros al coordinador"},
    {"code": "records.request_delete", "name": "Solicitar eliminación", "description": "Permite solicitar eliminación de registros"},
    {"code": "records.approve_delete", "name": "Aprobar eliminación", "description": "Permite aprobar/rechazar solicitudes de eliminación"},
    {"code": "identity.manage_users", "name": "Gestionar usuarios", "description": "Alta, cambio de niveles y activación/desactivación"},
    {"code": "certificates.read", "name": "Consultar certificados", "description": "Permite consultar certificados emitidos"},
    {"code": "audit.read", "name": "Consultar bitácora", "description": "Permite consultar la bitácora de auditoría"},
    {"code": "templates.manage", "name": "Gestionar plantillas", "description": "Permite crear, editar y desactivar plantillas"},
]

BASE_LEVELS = [
    {"code": 1, "name": "Nivel 1 - Administradores del sistema", "description": "CRUD completo, administración total"},
    {"code": 2, "name": "Nivel 2 - Coordinadores de área", "description": "CRU, gestión por área sin eliminación"},
    {"code": 3, "name": "Nivel 3 - Personal operativo", "description": "CR, consulta y creación"},
    {"code": 4, "name": "Nivel 4 - Personal externo", "description": "C, solo creación (becarios, voluntarios, servicio social, recepción)"},
]

BASE_AREAS = [
    {"name": "Administración", "description": "Área administrativa"},
    {"name": "Legal", "description": "Área de asesoría legal y documentación"},
    {"name": "Psicosocial", "description": "Área de atención psicosocial"},
    {"name": "Humanitario", "description": "Área de atención humanitaria directa"},
    {"name": "Comunicación", "description": "Área de comunicación y difusión"},
]

# Permisos asignados a cada rol
ROLE_DEFINITIONS = {
    "SYSTEM_ADMIN": {
        "description": "Administrador del sistema",
        "level_code": 1,
        "area_scoped": False,
        "permissions": [
            "records.create", "records.read", "records.edit", "records.delete",
            "records.channel", "records.request_delete", "records.approve_delete",
            "identity.manage_users", "certificates.read", "audit.read", "templates.manage",
        ],
    },
    "AREA_COORDINATOR": {
        "description": "Coordinador de área",
        "level_code": 2,
        "area_scoped": True,
        "permissions": [
            "records.create", "records.read", "records.edit",
            "records.channel", "records.request_delete",
        ],
    },
    "AREA_OPERATOR": {
        "description": "Personal operativo",
        "level_code": 3,
        "area_scoped": True,
        "permissions": [
            "records.create", "records.read", "records.channel",
        ],
    },
    "EXTERNAL_STAFF": {
        "description": "Personal externo",
        "level_code": 4,
        "area_scoped": False,
        "permissions": [
            "records.create",
        ],
    },
}

# Usuarios base — 1 por nivel con jerarquía real
# Cadena: Externo(4) → Operativo(3) → Coordinador(2) ← Admin(1)
BASE_USERS = [
    # ── Admin (1) ──
    {
        "full_name": settings.ADMIN_FULL_NAME,
        "email": settings.ADMIN_EMAIL.lower(),
        "password": settings.ADMIN_PASSWORD,
        "level_code": 1,
        "role_name": "SYSTEM_ADMIN",
        "area_name": "Administración",
    },
    # ── Coordinador (2) ──
    {
        "full_name": "Miguel Ángel Díaz Ortiz",
        "email": "coordinador@demo.org",
        "password": "CoordHuman2026!",
        "level_code": 2,
        "role_name": "AREA_COORDINATOR",
        "area_name": "Humanitario",
        "coordinator_area": "humanitario",
    },
    # ── Operativo (3) — asignado al coordinador ──
    {
        "full_name": "Carlos Hernández Ruiz",
        "email": "operador@demo.org",
        "password": "Oper2026Seguro!",
        "level_code": 3,
        "role_name": "AREA_OPERATOR",
        "area_name": "Humanitario",
        "assigned_to_email": "coordinador@demo.org",
    },
    # ── Externo (4) — asignado al operativo ──
    {
        "full_name": "Ana Martínez Soto",
        "email": "voluntario@demo.org",
        "password": "Voluntario2026!",
        "level_code": 4,
        "role_name": "EXTERNAL_STAFF",
        "area_name": "Humanitario",
        "user_subtype": "voluntario",
        "assigned_to_email": "operador@demo.org",
    },
]

# Registros de migrantes de ejemplo
DEMO_RECORDS = [
    {
        "name_or_alias": "Juan Pérez",
        "nationality": "Honduras",
        "language": "Español",
        "age_range": "25-34",
        "gender": "Masculino",
        "needs": ["alimentación", "alojamiento", "atención médica"],
        "observations": "Llegó acompañado de un menor. Requiere atención médica básica.",
        "status": "REGISTRADO",
        "area_name": "Humanitario",
    },
    {
        "name_or_alias": "María del Carmen",
        "nationality": "Guatemala",
        "language": "Español, Q'eqchi'",
        "age_range": "35-44",
        "gender": "Femenino",
        "needs": ["apoyo legal", "documentación"],
        "observations": "Solicitante de asilo. Documentación en proceso.",
        "status": "EN_PROCESO",
        "area_name": "Legal",
    },
    {
        "name_or_alias": "Roberto L.",
        "nationality": "El Salvador",
        "language": "Español",
        "age_range": "18-24",
        "gender": "Masculino",
        "needs": ["alimentación", "transporte"],
        "observations": "Tránsito hacia el norte. Apoyo con alimentación y hospedaje temporal.",
        "status": "ATENDIDO",
        "area_name": "Humanitario",
    },
    {
        "name_or_alias": "Familia Gómez",
        "nationality": "Venezuela",
        "language": "Español",
        "age_range": "(grupo familiar)",
        "gender": "N/A",
        "needs": ["alojamiento", "alimentación", "comunicación"],
        "observations": "Grupo familiar de 4 personas. Niños en edad escolar.",
        "status": "REGISTRADO",
        "area_name": "Psicosocial",
    },
    {
        "name_or_alias": "Pedro S.",
        "nationality": "Nicaragua",
        "language": "Español",
        "age_range": "45-54",
        "gender": "Masculino",
        "needs": ["apoyo psicológico"],
        "observations": "Caso cerrado. Reubicación completada.",
        "status": "CERRADO",
        "area_name": "Psicosocial",
    },
]

# Plantilla base
BASE_TEMPLATE_FIELDS = [
    {"name": "name_or_alias", "label": "Nombre o alias", "field_type": "text", "required": True},
    {"name": "nationality", "label": "Nacionalidad / País de origen", "field_type": "text", "required": False},
    {"name": "language", "label": "Idioma principal", "field_type": "text", "required": False},
    {"name": "age_range", "label": "Rango de edad", "field_type": "select", "required": False,
     "options": ["Menor de 18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+", "(grupo familiar)"]},
    {"name": "gender", "label": "Género / Autodescripción", "field_type": "text", "required": False},
    {"name": "contact_info", "label": "Medio de contacto", "field_type": "text", "required": False},
    {"name": "needs", "label": "Necesidades principales", "field_type": "multiselect", "required": False,
     "options": ["alimentación", "alojamiento", "atención médica", "apoyo psicológico",
                  "apoyo legal", "documentación", "transporte", "comunicación"]},
    {"name": "observations", "label": "Observaciones iniciales", "field_type": "textarea", "required": False},
    {"name": "status", "label": "Estatus del caso", "field_type": "select", "required": True,
     "options": ["REGISTRADO", "EN_PROCESO", "ATENDIDO", "CERRADO"]},
]


# ──────────────────────────────────────────────────────────────────
#  Helpers de creación idempotente
# ──────────────────────────────────────────────────────────────────

def get_or_create_permission(db: Session, data: dict) -> Permission:
    permission = db.query(Permission).filter(Permission.code == data["code"]).first()
    if permission:
        permission.name = data["name"]
        permission.description = data.get("description")
        db.add(permission)
        db.flush()
        return permission
    permission = Permission(**data)
    db.add(permission)
    db.flush()
    return permission


def get_or_create_level(db: Session, data: dict) -> AccessLevel:
    level = db.query(AccessLevel).filter(AccessLevel.code == data["code"]).first()
    if level:
        level.name = data["name"]
        level.description = data.get("description")
        db.add(level)
        db.flush()
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
    permission_codes: list,
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


def create_base_user(
    db: Session,
    user_data: dict,
    roles_by_name: dict,
    areas_by_name: dict,
    levels_by_code: dict,
) -> User:
    """Crea un usuario base ACTIVE con contraseña, credencial y certificado."""
    existing = db.query(User).filter(User.email == user_data["email"]).first()
    if existing:
        print(f"  Usuario {user_data['email']} ya existe, omitido.")
        return existing

    role = roles_by_name[user_data["role_name"]]
    area = areas_by_name.get(user_data["area_name"]) if user_data.get("area_name") else None
    level = levels_by_code[user_data["level_code"]]

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=365)

    user = User(
        full_name=user_data["full_name"],
        email=user_data["email"],
        status="ACTIVE",
        is_active=True,
        area_id=area.id if area else None,
        access_level_id=level.id,
        role_id=role.id,
        created_by_id=None,
        starts_at=now,
        expires_at=expires_at,
        user_subtype=user_data.get("user_subtype"),
        coordinator_area=user_data.get("coordinator_area"),
    )
    db.add(user)
    db.flush()

    # Credencial (password_hash vive aquí, no en User)
    credential = Credential(
        user_id=user.id,
        identity_provider="local",
        username=user.email,
        password_hash=get_password_hash(user_data["password"]),
        password_updated_at=now,
    )
    db.add(credential)
    db.flush()

    # Certificado criptográfico de identidad
    cert = CryptoService.issue_certificate(db, user, expires_at, issued_by=user.id)

    # Audit entry
    db.add(AuditLog(
        actor_user_id=user.id,
        action="identity.create_user",
        resource="user",
        resource_id=str(user.id),
        result="SUCCESS",
        detail=f"[SEED] Usuario base creado con nivel {user_data['level_code']}",
    ))
    db.add(AuditLog(
        actor_user_id=user.id,
        action="certificates.issue",
        resource="certificate",
        resource_id=str(cert.id),
        result="SUCCESS",
        detail=f"[SEED] Certificado emitido para {user.email}",
        hash_related=cert.fingerprint,
        certificate_id=cert.id,
    ))

    db.flush()
    area_label = user_data.get("area_name") or "Sin área"
    print(f"  [OK] {user.email} | Nivel: {user_data['level_code']} | Área: {area_label} | Cert: {cert.serial_number[:12]}...")
    return user


def create_demo_records(db: Session, admin_user: User, areas_by_name: dict) -> None:
    """Crea registros de migrantes de ejemplo con hashes SHA-256."""
    existing = db.query(MigrantRecord).count()
    if existing > 0:
        print(f"  Ya existen {existing} registros, omitidos.")
        return

    now = datetime.now(timezone.utc)
    year = now.year

    for i, rec_data in enumerate(DEMO_RECORDS):
        area = areas_by_name.get(rec_data["area_name"])
        area_id = area.id if area else None
        folio = f"CM-{year}-{(i + 1):04d}"

        needs_json = json.dumps(rec_data.get("needs", []), ensure_ascii=False)

        record = MigrantRecord(
            folio=folio,
            name_or_alias=rec_data["name_or_alias"],
            nationality=rec_data["nationality"],
            language=rec_data.get("language"),
            age_range=rec_data.get("age_range"),
            gender=rec_data.get("gender"),
            needs=needs_json,
            registration_date=now - timedelta(days=len(DEMO_RECORDS) - i),
            observations=rec_data["observations"],
            area_id=area_id,
            status=rec_data["status"],
            created_by_id=admin_user.id,
            updated_by_id=admin_user.id,
        )
        db.add(record)
        db.flush()

        # Calcular hash
        hashable = {
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
        record.sha256_hash = CryptoService.compute_record_hash(hashable)
        db.add(record)
        db.flush()

        # Audit
        db.add(AuditLog(
            actor_user_id=admin_user.id,
            action="records.create",
            resource="migrant_record",
            resource_id=str(record.id),
            result="SUCCESS",
            detail=f"[SEED] Registro: {record.folio} - {record.name_or_alias}",
            hash_related=record.sha256_hash,
        ))

        print(f"  [OK] Registro: {record.folio} - {record.name_or_alias} | Hash: {record.sha256_hash[:16]}...")

    db.flush()


def create_base_template(db: Session, admin_user: User) -> None:
    """Crea la plantilla base de registro de migrantes."""
    existing = db.query(Template).filter(Template.name == "Registro básico de migrante").first()
    if existing:
        print("  Plantilla base ya existe, omitida.")
        return

    template = Template(
        name="Registro básico de migrante",
        description="Plantilla inicial de captura con campos genéricos y prudentes para registro de persona migrante.",
        fields_json=json.dumps(BASE_TEMPLATE_FIELDS, ensure_ascii=False),
        is_active=True,
        created_by_id=admin_user.id,
    )
    db.add(template)
    db.flush()

    db.add(AuditLog(
        actor_user_id=admin_user.id,
        action="templates.create",
        resource="template",
        resource_id=str(template.id),
        result="SUCCESS",
        detail=f"[SEED] Plantilla base creada: {template.name}",
    ))

    print(f"  [OK] Plantilla: {template.name}")


# ──────────────────────────────────────────────────────────────────
#  Seed principal
# ──────────────────────────────────────────────────────────────────

def seed() -> None:
    db = SessionLocal()
    try:
        print("=== Seed: Niveles de acceso ===")
        for level_data in BASE_LEVELS:
            get_or_create_level(db, level_data)

        print("=== Seed: Áreas ===")
        for area_data in BASE_AREAS:
            get_or_create_area(db, area_data)

        print("=== Seed: Permisos ===")
        for permission_data in BASE_PERMISSIONS:
            get_or_create_permission(db, permission_data)

        db.flush()

        # Lookup tables
        levels_by_code = {lv.code: lv for lv in db.query(AccessLevel).all()}

        print("=== Seed: Roles ===")
        for role_name, role_def in ROLE_DEFINITIONS.items():
            level = levels_by_code[role_def["level_code"]]
            get_or_create_role(
                db,
                name=role_name,
                description=role_def["description"],
                level=level,
                permission_codes=role_def["permissions"],
                area_scoped=role_def["area_scoped"],
            )

        db.flush()

        # Preparar lookup tables
        roles_by_name = {r.name: r for r in db.query(Role).all()}
        areas_by_name = {a.name: a for a in db.query(Area).all()}

        print("=== Seed: Usuarios base ===")
        users = []
        for user_data in BASE_USERS:
            u = create_base_user(db, user_data, roles_by_name, areas_by_name, levels_by_code)
            users.append(u)

        # Asignar jerarquías (assigned_to_id)
        users_by_email = {u.email: u for u in users}
        for user_data in BASE_USERS:
            assigned_to_email = user_data.get("assigned_to_email")
            if assigned_to_email and assigned_to_email in users_by_email:
                target_user = users_by_email[user_data["email"]]
                assigned_to = users_by_email[assigned_to_email]
                target_user.assigned_to_id = assigned_to.id
                db.add(target_user)
                print(f"  [JERARQUIA] {target_user.email} -> {assigned_to.email}")
        db.flush()

        admin_user = users[0]

        print("=== Seed: Registros de migrantes demo ===")
        create_demo_records(db, admin_user, areas_by_name)

        print("=== Seed: Plantilla base ===")
        create_base_template(db, admin_user)

        db.commit()
        print("\n[OK] Seed completado correctamente.")
        print("\n--- Credenciales de usuarios base ---")
        for ud in BASE_USERS:
            area_label = ud.get("area_name") or "Sin área"
            print(f"  {ud['email']} / {ud['password']} (Nivel {ud['level_code']}, {area_label})")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
