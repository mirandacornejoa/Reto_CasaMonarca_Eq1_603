import apiClient from "./client";

export async function listRecords({ area_id, status, search, limit } = {}) {
  const params = {};
  if (area_id) params.area_id = area_id;
  if (status) params.status = status;
  if (search) params.search = search;
  if (limit) params.limit = limit;
  const { data } = await apiClient.get("/records/", { params });
  return data;
}

export async function getRecord(id) {
  const { data } = await apiClient.get(`/records/${id}`);
  return data;
}

export async function createRecord(payload) {
  const { data } = await apiClient.post("/records/", payload);
  return data;
}

export async function updateRecord(id, payload) {
  const { data } = await apiClient.patch(`/records/${id}`, payload);
  return data;
}

export async function getRecordHash(id) {
  const { data } = await apiClient.get(`/records/${id}/hash`);
  return data;
}
