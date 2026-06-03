# Casa Monarca — Sistema de Gestión de Migrantes

Sistema full-stack para gestión de registros de migrantes con control de acceso por roles (RBAC), firma digital, solicitudes ARCO, bitácora de auditoría y certificados criptográficos. Desarrollado para Casa Monarca A.C.

## Estructura del proyecto

```
management_system/
├── backend/          # FastAPI + SQLAlchemy + Alembic
├── frontend/         # React + Vite
└── docs/             # Notas técnicas
```

## Requisitos previos

- **Python 3.10+**
- **Node.js 18+**
- Git

> La base de datos usa **SQLite** por defecto — no requiere instalar MySQL.

---

## Instalación y puesta en marcha

### 1. Clonar el repositorio

```bash
git clone https://github.com/mirandacornejoa/Reto_CasaMonarca_Eq1_603.git
cd Reto_CasaMonarca_Eq1_603
```

### 2. Backend

```bash
cd backend

# Crear entorno virtual
python -m venv .venv

# Activar (Windows)
.venv\Scripts\activate
# Activar (macOS/Linux)
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

> El archivo `.env` ya viene preconfigurado para SQLite local. No necesitas cambiar nada para desarrollo.

### 3. Inicializar base de datos y cargar datos demo

```bash
# Desde la carpeta backend/ con el entorno virtual activo:
python scripts/reset_and_seed.py
```

Este script:
- Borra la BD anterior (si existe)
- Crea todas las tablas
- Carga los 4 usuarios demo con certificados criptográficos
- Carga registros de migrantes de ejemplo

### 4. Levantar el backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API disponible en: `http://localhost:8000/api/v1`  
Swagger UI: `http://localhost:8000/docs`

### 5. Frontend

```bash
cd frontend
npm install

copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

npm run dev
```

Frontend disponible en: `http://localhost:5173`

---

## Credenciales demo

| Rol | Email | Contraseña | Nivel |
|-----|-------|------------|-------|
| Administrador | `admin@demo.org` | `Admin2026Seguro!` | 1 |
| Coordinador | `coordinador@demo.org` | `CoordHuman2026!` | 2 |
| Operativo | `operador@demo.org` | `Oper2026Seguro!` | 3 |
| Voluntario (externo) | `voluntario@demo.org` | `Voluntario2026!` | 4 |

---

## Resetear la base de datos

Si quieres volver al estado inicial limpio:

```bash
cd backend
python scripts/reset_and_seed.py
```

---

## Módulos del sistema

### Gestión de registros
- Crear, editar y consultar registros de migrantes
- Cada registro tiene hash SHA-256 de integridad
- Flujo de trabajo: pendiente → canalizado → revisado

### Control de acceso (RBAC)
- **Nivel 1 (Admin)**: CRUD completo, gestión de usuarios, bitácora, aprobación de cancelaciones ARCO
- **Nivel 2 (Coordinador)**: Registros CRU, atención de solicitudes ARCO, peticiones de eliminación
- **Nivel 3 (Operativo)**: Crear y consultar registros, crear solicitudes ARCO
- **Nivel 4 (Externo/Voluntario)**: Solo crear registros

### Módulo ARCO (Acceso, Rectificación, Cancelación, Oposición)
- Operativo crea solicitud ARCO desde un registro
- Coordinador atiende (con firma digital) ACCESS, RECTIFICATION, OPPOSITION
- CANCELLATION se escala al administrador para aprobación/rechazo (con firma)
- Al aprobar una cancelación: el registro se anonimiza automáticamente

### Peticiones de eliminación
- Coordinador solicita eliminación de un registro al administrador
- Admin aprueba o rechaza con justificación

### Firma digital
- Coordinadores y admin firman resoluciones con archivo `.key` (clave privada)
- Las firmas son verificables con el certificado público `.cer`

### Bitácora de auditoría
- Registro completo de todas las acciones del sistema
- Acceso exclusivo para administradores

---

## Arquitectura de seguridad

- **Contraseñas**: `passlib + bcrypt`
- **Sesiones**: JWT con `python-jose`
- **Integridad de registros**: SHA-256 con `hashlib`
- **Certificados de identidad**: ECDSA (secp256r1) con `cryptography`
- **Firma de resoluciones**: ECDSA con clave privada cifrada AES-128-CBC
- **RBAC**: validación por nivel de acceso en cada endpoint
- **Vigencia de usuarios**: validación en login y en cada request

---

## Endpoints principales

### Auth
- `POST /api/v1/auth/login` — Login
- `GET /api/v1/auth/me` — Usuario actual

### Registros
- `GET /api/v1/records/` — Listar
- `POST /api/v1/records/` — Crear
- `PUT /api/v1/records/{id}` — Editar
- `GET /api/v1/records/{id}` — Detalle + hash

### ARCO
- `GET /api/v1/arco/` — Listar (filtrado por rol)
- `POST /api/v1/arco/` — Crear solicitud
- `PUT /api/v1/arco/{id}/attend` — Atender (firma requerida)
- `PUT /api/v1/arco/{id}/escalate` — Escalar al admin
- `PUT /api/v1/arco/{id}/review` — Aprobar/rechazar (admin, firma requerida)

### Peticiones de eliminación
- `GET /api/v1/deletion-requests/` — Listar
- `POST /api/v1/deletion-requests/` — Crear petición
- `PUT /api/v1/deletion-requests/{id}/review` — Aprobar/rechazar (admin)

### Dashboard
- `GET /api/v1/dashboard/` — Panel de trabajo por rol

### Usuarios (admin)
- `GET /api/v1/users/` — Listar usuarios
- `POST /api/v1/identity/collaborators` — Crear colaborador
- `PATCH /api/v1/users/{id}/level` — Cambiar nivel
- `PATCH /api/v1/users/{id}/status` — Activar/desactivar

### Auditoría (admin)
- `GET /api/v1/audit/` — Bitácora completa

---

## Equipo

Equipo 1 — Grupo 603 · Tecnológico de Monterrey  
Reto Casa Monarca A.C.
