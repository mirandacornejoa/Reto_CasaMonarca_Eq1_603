import apiClient from "./client";

export const createArcoRequest = (payload) =>
  apiClient.post("/arco-requests/", payload).then((r) => r.data);

export const listArcoRequests = () =>
  apiClient.get("/arco-requests/").then((r) => r.data);

export const getArcoRequest = (id) =>
  apiClient.get(`/arco-requests/${id}`).then((r) => r.data);

export const attendArcoRequest = (id, resolution_notes, content_hash, signature_b64) =>
  apiClient.put(`/arco-requests/${id}/attend`, { resolution_notes, content_hash, signature_b64 }).then((r) => r.data);

export const escalateArcoRequest = (id, notes) =>
  apiClient.put(`/arco-requests/${id}/escalate`, { notes }).then((r) => r.data);

export const reviewArcoRequest = (id, action, resolution_notes, content_hash, signature_b64) =>
  apiClient.put(`/arco-requests/${id}/review`, { action, resolution_notes, content_hash, signature_b64 }).then((r) => r.data);
