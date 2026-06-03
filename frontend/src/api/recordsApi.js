import apiClient from "./client";

export async function listRecords({ area_id, status, workflow_status, search, limit } = {}) {
  const params = {};
  if (area_id) params.area_id = area_id;
  if (status) params.status = status;
  if (workflow_status) params.workflow_status = workflow_status;
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

export async function updateRecord(id, payload, signatureData = null) {
  const body = { ...payload };
  if (signatureData) {
    body.content_hash = signatureData.contentHash;
    body.signature_b64 = signatureData.signatureB64;
  }
  const { data } = await apiClient.patch(`/records/${id}`, body);
  return data;
}

export async function deleteRecordSigned(id, signatureData) {
  const { data } = await apiClient.delete(`/records/${id}`, {
    data: {
      content_hash: signatureData.contentHash,
      signature_b64: signatureData.signatureB64,
    },
  });
  return data;
}

export async function getRecordHash(id) {
  const { data } = await apiClient.get(`/records/${id}/hash`);
  return data;
}

export async function deleteRecord(id) {
  const { data } = await apiClient.delete(`/records/${id}`);
  return data;
}

export async function getResourceSignatures(resourceType, resourceId) {
  const { data } = await apiClient.get(`/auth/signing/signatures/${resourceType}/${resourceId}`);
  return data;
}

// ── Workflow operativo ──

export async function reviewRecord(recordId, payload = {}) {
  const { data } = await apiClient.put(`/records/${recordId}/review`, payload);
  return data;
}

export async function channelRecord(recordId, notes) {
  const { data } = await apiClient.put(`/records/${recordId}/channel`, { notes: notes || null });
  return data;
}

export async function closeRecord(recordId) {
  const { data } = await apiClient.put(`/records/${recordId}/close`);
  return data;
}

