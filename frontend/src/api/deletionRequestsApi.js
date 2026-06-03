import apiClient from "./client";

export async function createDeletionRequest(payload) {
  const { data } = await apiClient.post("/deletion-requests/", payload);
  return data;
}

export async function listDeletionRequests(status) {
  const params = status ? { status } : {};
  const { data } = await apiClient.get("/deletion-requests/", { params });
  return data;
}

export async function getDeletionRequest(requestId) {
  const { data } = await apiClient.get(`/deletion-requests/${requestId}`);
  return data;
}

export async function reviewDeletionRequest(requestId, payload) {
  const { data } = await apiClient.put(
    `/deletion-requests/${requestId}/review`,
    payload
  );
  return data;
}
