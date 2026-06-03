import apiClient from "./client";

export async function listAuditLogs(limit = 200, matricula = "") {
  const params = { limit };
  if (matricula) params.matricula = matricula;
  const { data } = await apiClient.get("/audit/", { params });
  return data;
}
