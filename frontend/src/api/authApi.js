import apiClient from "./client";

export async function login(email, password) {
  const body = new URLSearchParams();
  body.append("username", email);
  body.append("password", password);

  const { data } = await apiClient.post("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function getMe() {
  const { data } = await apiClient.get("/auth/me");
  return data;
}

export async function activateAccount(token, password) {
  const { data } = await apiClient.post("/auth/activate", { token, password });
  return data;
}
