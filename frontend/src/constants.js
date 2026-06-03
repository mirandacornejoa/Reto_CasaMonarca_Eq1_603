export const ADMIN_ACCESS_LEVEL_CODE = 1;
export const COORDINATOR_LEVEL_CODE = 2;
export const OPERATOR_LEVEL_CODE = 3;
export const EXTERNAL_LEVEL_CODE = 4;

export const TOKEN_KEY = "ims_token";

// Subtipos de usuario (nivel 4)
export const USER_SUBTYPES = [
  { value: "becario", label: "Becario" },
  { value: "voluntario", label: "Voluntario" },
  { value: "servicio_social", label: "Servicio Social" },
  { value: "recepcion", label: "Recepción" },
];

// Áreas de coordinador (nivel 2)
export const COORDINATOR_AREAS = [
  { value: "administracion", label: "Administración" },
  { value: "legal", label: "Legal" },
  { value: "psicosocial", label: "Psicosocial" },
  { value: "humanitario", label: "Humanitario" },
  { value: "comunicacion", label: "Comunicación" },
];

// Estados de workflow visibles
export const WORKFLOW_STATUSES = [
  { value: "pendiente", label: "Pendiente", color: "#f59e0b" },
  { value: "revisado", label: "Revisado", color: "#3b82f6" },
];

// Opciones de género
export const GENDER_OPTIONS = [
  "Femenino",
  "Masculino",
  "No-binario",
  "LGBTIQ+",
];

// Estado civil
export const CIVIL_STATUS_OPTIONS = [
  "Casada / Casado",
  "Divorciada / Divorciado",
  "Soltera / Soltero",
  "Separada / Separado",
  "Viuda / Viudo",
  "Unión Libre",
  "Otras",
];

// Rangos de edad
export const AGE_RANGE_OPTIONS = [
  "0 - 11 meses",
  ...Array.from({ length: 90 }, (_, i) => String(i + 1)),
];

// Grupos de población
export const POPULATION_GROUPS = [
  "Adulto (18-59 años)",
  "Adulto mayor (+60 años)",
  "Niña acompañada",
  "Niño acompañado",
  "Adolescente hombre acompañado",
  "Adolescente mujer acompañada",
  "NNA No acompañado",
];

// Estados de registro legacy (retrocompat)
export const RECORD_STATUSES = [
  "REGISTRADO",
  "EN_PROCESO",
  "ATENDIDO",
  "CERRADO",
];

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

export function getWorkflowBadgeClass(status) {
  const map = {
    pendiente: "badge-pending",
    revisado: "badge-valid",
  };
  return map[status] || "badge-inactive";
}
