# Identity Access Demo - Sprint 1

Proyecto full-stack (monolito modular con frontend separado) para gestión de identidades, niveles de acceso y auditoría, compatible con hosting limitado orientado a Python + MySQL + frontend estático.

## Estructura

- `backend/` FastAPI + SQLAlchemy + Alembic + JWT + seed
- `frontend/` React + Vite (JavaScript)
- `docs/` notas del sprint

## Requisitos

- Python 3.9
- Node.js 18+
- MySQL 8.0 (opcional para local; fallback SQLite disponible)

## Backend - ejecución local

1. Crear entorno virtual e instalar dependencias:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Configurar entorno:

```bash
copy .env.example .env
```

3. Crear esquema de BD:

Opción A (recomendada): Alembic

```bash
alembic upgrade head
```

Opción B (rápida demo): `AUTO_CREATE_TABLES=true` crea tablas al arrancar.

4. Seed inicial:

```bash
python -m scripts.seed_initial_data
```

5. Ejecutar API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API base: `http://localhost:8000/api/v1`

## Frontend - ejecución local

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend: `http://localhost:5173`

## Flujo demo cubierto

1. Login admin (`admin@demo.org` / `Admin123!`)
2. Alta de colaborador con área y nivel
3. Generación de activación (SMTP real o enlace demo)
4. Activación de cuenta por token
5. Listado de usuarios
6. Cambio de nivel/rol implícito por nivel
7. Desactivación/reactivación
8. Registro de auditoría

## Endpoints principales

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/activate`
- `POST /api/v1/identity/collaborators` (admin)
- `GET /api/v1/identity/areas` (admin)
- `GET /api/v1/users/` (admin)
- `PATCH /api/v1/users/{user_id}/level` (admin)
- `PATCH /api/v1/users/{user_id}/status` (admin)
- `GET /api/v1/audit/` (admin)
- `GET /api/v1/documents/placeholder`
- `GET /api/v1/verification/placeholder`

## Seed inicial

El seed crea:

- 4 niveles de acceso base
- permisos funcionales I-IV + permiso de gestión de usuarios
- 4 roles base mapeados a niveles
- 2 áreas de ejemplo
- 1 administrador inicial

## Notas de seguridad / demo

- Contraseñas con `passlib + bcrypt`.
- JWT para autenticación.
- Tokens de activación almacenados por hash SHA-256.
- Modo SMTP opcional; sin SMTP se devuelve enlace de activación en respuesta para pruebas locales.

## Sprint 2 (placeholder ya preparado)

- Firma digital de documentos
- Verificación pública de folio/hash
- Gestión documental completa
- Certificados criptográficos reales
