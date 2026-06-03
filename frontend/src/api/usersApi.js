import apiClient from "./client";

export async function createCollaborator(payload) {
  const { data } = await apiClient.post("/identity/collaborators", payload);
  return data;
}

export async function listUsers() {
  const { data } = await apiClient.get("/identity/users");
  return data;
}

export async function updateUserLevel(userId, payload) {
  const { data } = await apiClient.patch(`/identity/users/${userId}/level`, payload);
  return data;
}

export async function updateUserStatus(userId, isActive) {
  const { data } = await apiClient.patch(`/identity/users/${userId}/status`, { is_active: isActive });
  return data;
}

export async function revokeUser(userId) {
  const { data } = await apiClient.patch(`/identity/users/${userId}/revoke`);
  return data;
}

export async function reactivateUser(userId) {
  const { data } = await apiClient.patch(`/identity/users/${userId}/reactivate`);
  return data;
}

export async function updateUserExpiry(userId, payload) {
  const { data } = await apiClient.patch(`/identity/users/${userId}/expiry`, payload);
  return data;
}

export async function getUserCertificate(userId) {
  const { data } = await apiClient.get(`/identity/users/${userId}/certificate`);
  return data;
}

export async function reissueCertificate(userId) {
  const { data } = await apiClient.post(`/identity/users/${userId}/certificate/reissue`);
  return data;
}

export async function listAreas() {
  const { data } = await apiClient.get("/identity/areas");
  return data;
}

export async function listLevels() {
  const { data } = await apiClient.get("/roles/levels");
  return data;
}

export async function listRoles() {
  const { data } = await apiClient.get("/roles/");
  return data;
}

export async function listOperators() {
  const { data } = await apiClient.get("/identity/operators");
  return data;
}

export async function listCoordinators() {
  const { data } = await apiClient.get("/identity/coordinators");
  return data;
}

export async function updateUserAssignment(userId, assignedToId) {
  const { data } = await apiClient.patch(`/identity/users/${userId}/assignment`, {
    assigned_to_id: assignedToId || null,
  });
  return data;
}

