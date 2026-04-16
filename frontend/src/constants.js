// Nivel de acceso que corresponde al Administrador del Sistema (código 1)
export const ADMIN_ACCESS_LEVEL_CODE = 1;
export const COORDINATOR_LEVEL_CODE = 2;
export const OPERATOR_LEVEL_CODE = 3;
export const EXTERNAL_LEVEL_CODE = 4;

// Clave del token JWT en localStorage
export const TOKEN_KEY = "ims_token";

export function getStatusBadgeClass(status) {
  const map = {
    ACTIVE: "badge-active",
    INACTIVE: "badge-inactive",
    PENDING: "badge-pending",
    EXPIRED: "badge-expired",
    REVOKED: "badge-revoked",
    VALID: "badge-valid",
  };
  return map[status] || "badge-inactive";
}
