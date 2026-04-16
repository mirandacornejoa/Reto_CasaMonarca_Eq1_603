import apiClient from "./client";

export async function listTemplates(activeOnly = false) {
  const { data } = await apiClient.get("/templates/", { params: { active_only: activeOnly } });
  return data;
}

export async function createTemplate(payload) {
  const { data } = await apiClient.post("/templates/", payload);
  return data;
}

export async function updateTemplate(id, payload) {
  const { data } = await apiClient.patch(`/templates/${id}`, payload);
  return data;
}

export async function updateTemplateStatus(id, isActive) {
  const { data } = await apiClient.patch(`/templates/${id}/status`, { is_active: isActive });
  return data;
}
