# Sprint 1 - Estado de implementación

## Implementado en este sprint

- Login con JWT (`/api/v1/auth/login`) y perfil actual (`/api/v1/auth/me`).
- Alta de colaboradores por administrador con área y nivel (`/api/v1/identity/collaborators`).
- Proceso de activación con token (`/api/v1/auth/activate`).
- Gestión de usuarios por admin: listado, cambio de nivel y cambio de estado.
- Auditoría en acciones críticas: login, alta, activación, cambios de nivel y estado.
- Seed inicial de niveles, permisos, roles, áreas y usuario administrador.
- Frontend React con rutas protegidas, login, activación y panel de usuarios.
- Integración SMTP opcional con modo demo de enlace de activación.

## Preparado como placeholder para sprint 2

- Módulo documental (`documents`) con tabla y ruta placeholder.
- Módulo de verificación pública (`verification`) con ruta placeholder.
- Servicio de criptografía base con SHA-256 y stubs de firma digital.
- Tabla de certificados como entidad separada de credenciales de acceso.

## Credenciales iniciales demo

- Usuario: `admin@demo.org`
- Contraseña: `Admin123!`

Se pueden ajustar desde variables de entorno antes de correr el seed.
