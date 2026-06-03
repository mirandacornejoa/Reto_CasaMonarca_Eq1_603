import apiClient from "./client";

export const getSignatureStatus = (resourceType, resourceId) =>
  apiClient.get(`/signatures/${resourceType}/${resourceId}`).then((r) => r.data);

export const verifySignature = (resourceType, resourceId) =>
  apiClient.post(`/signatures/${resourceType}/${resourceId}/verify`).then((r) => r.data);

export const verifyCertSignature = (resourceType, resourceId, certPem) =>
  apiClient.post(`/signatures/${resourceType}/${resourceId}/verify-cert`, { cert_pem: certPem }).then((r) => r.data);
