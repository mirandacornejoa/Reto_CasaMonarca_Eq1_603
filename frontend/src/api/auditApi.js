import apiClient from "./client";

export async function listAuditLogs(limit = 200) {
  const { data } = await apiClient.get("/audit/", { params: { limit } });
  return data;
}
