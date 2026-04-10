import apiClient from "./client";

export async function createCollaborator(payload) {
  const { data } = await apiClient.post("/identity/collaborators", payload);
  return data;
}

export async function listUsers() {
  const { data } = await apiClient.get("/users/");
  return data;
}

export async function updateUserLevel(userId, payload) {
  const { data } = await apiClient.patch(`/users/${userId}/level`, payload);
  return data;
}

export async function updateUserStatus(userId, isActive) {
  const { data } = await apiClient.patch(`/users/${userId}/status`, { is_active: isActive });
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
