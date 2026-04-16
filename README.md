# Identity Access Demo — Sprint 2

Proyecto full-stack (monolito modular con frontend separado) para gestión de identidades, niveles de acceso, certificados criptográficos internos, registros de migrantes y auditoría completa. Compatible con hosting limitado orientado a Python + MySQL + frontend estático.

## Estructura

- `backend/` FastAPI + SQLAlchemy + Alembic + JWT + seed
- `frontend/` React + Vite (JavaScript)
- `docs/` notas del sprint

## Requisitos

- Python 3.9+
- Node.js 18+
- MySQL 8.0 (opcional para local; fallback SQLite disponible)

## Backend — ejecución local

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

3. Eliminar BD anterior y crear esquema nuevo:

```bash
del app.db  # si existe
```

El servidor crea tablas automáticamente con `AUTO_CREATE_TABLES=true`.

4. Ejecutar API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. Seed inicial (ejecutar con el servidor detenido o en otra terminal):

```bash
python -m scripts.seed_initial_data
```

API base: `http://localhost:8000/api/v1`
Swagger UI: `http://localhost:8000/docs`

## Frontend — ejecución local

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend: `http://localhost:5173`

---

## Credenciales demo

| Rol | Email | Contraseña | Nivel |
|-----|-------|------------|-------|
| Administrador | `admin@demo.org` | `Admin123!` | 1 |
| Coordinador | `coordinador@demo.org` | `Coord123!` | 2 |
| Operador | `operador@demo.org` | `Oper123!` | 3 |
| Externo | `externo@demo.org` | `Ext123!` | 4 |

---

## Flujo demo cubierto

1. Login con cualquiera de los 4 usuarios demo
2. Admin: gestión completa de usuarios (crear, cambiar rol, activar/desactivar, definir vigencia)
3. Al crear usuario se emite **certificado criptográfico interno RSA-2048** con fingerprint SHA-256
4. Cada rol ve funciones distintas (RBAC por nivel de acceso)
5. Módulo de registros de migrantes: crear, listar, consultar, editar (niveles 1-3)
6. Cada registro tiene hash SHA-256 calculado y verificable
7. Bitácora de auditoría completa (solo admin puede consultar)
8. Consulta de certificados emitidos (admin: todo; externo: vista pública)
9. Validación de estado de certificados
10. Vigencia de usuario: si expira, no puede operar

---

## Roles y permisos

### Nivel 1 — Administrador
- Gestionar usuarios (crear, roles, vigencia, activar/desactivar)
- Registros: crear, leer, editar
- Certificados: ver todos, detalle completo
- Bitácora: acceso total
- Hashes: consultar

### Nivel 2 — Coordinador
- Registros: crear, leer, editar
- NO gestiona usuarios
- NO ve bitácora global
- NO cambia roles

### Nivel 3 — Operador
- Registros: crear, leer, editar
- NO gestiona usuarios
- NO ve bitácora
- NO revisa certificados globalmente

### Nivel 4 — Externo
- Registros: solo lectura
- Certificados: consulta pública y validación
- NO edita nada
- NO ve bitácora

---

## Endpoints principales

### Auth
- `POST /api/v1/auth/login` — login con email y contraseña
- `GET /api/v1/auth/me` — información del usuario actual
- `POST /api/v1/auth/activate` — activar cuenta por token
- `GET /api/v1/auth/demo/activation-links` — links de activación demo (admin)

### Identity (admin)
- `POST /api/v1/identity/collaborators` — crear usuario con área, nivel y vigencia
- `GET /api/v1/identity/areas` — listar áreas

### Users (admin)
- `GET /api/v1/users/` — listar usuarios
- `PATCH /api/v1/users/{id}/level` — cambiar nivel/rol
- `PATCH /api/v1/users/{id}/status` — activar/desactivar

### Certificates
- `GET /api/v1/certificates/` — listar certificados (admin)
- `GET /api/v1/certificates/public` — vista pública (todos)
- `GET /api/v1/certificates/{id}` — detalle (admin)
- `GET /api/v1/certificates/validate/{id}` — validar estado (todos)

### Records
- `POST /api/v1/records/` — crear registro (niveles 1-3)
- `GET /api/v1/records/` — listar registros (todos)
- `GET /api/v1/records/{id}` — detalle con hash (todos)
- `PUT /api/v1/records/{id}` — editar registro (niveles 1-3)
- `GET /api/v1/records/{id}/hash` — consultar hash (todos, con audit)

### Audit (admin)
- `GET /api/v1/audit/` — bitácora completa

### Roles
- `GET /api/v1/roles/` — listar roles
- `GET /api/v1/roles/permissions` — listar permisos
- `GET /api/v1/roles/levels` — listar niveles de acceso

---

## Arquitectura de seguridad

- **Contraseñas**: `passlib + bcrypt`
- **JWT**: tokens de sesión con python-jose
- **Hashes**: SHA-256 con `hashlib` para tokens, registros, y certificados
- **Certificados internos**: RSA-2048 generados con `cryptography`, clave pública PEM como cert_data, fingerprint SHA-256
- **RBAC**: validación por nivel de acceso en cada endpoint
- **Vigencia**: validación de expiración tanto en login como en cada request autenticado
- **Auditoría**: registro de login, creación/desactivación de usuarios, emisión de certificados, CRUD de registros, consultas de hash

---

## Seed inicial

El seed crea:

- 4 niveles de acceso base
- 10 permisos funcionales (5 originales + 5 nuevos para records/certificates/audit)
- 4 roles base mapeados a niveles con permisos diferenciados
- 3 áreas de ejemplo
- 4 usuarios demo (uno por nivel), todos activos con certificados emitidos
- 5 registros de migrantes de ejemplo con hashes SHA-256
- Entradas de auditoría para todas las operaciones del seed

---

## Sprint 3 (pendiente)

- Frontend demo completo con vistas por rol
- Firma digital de documentos
- Verificación pública de folio/hash
- Gestión documental completa
