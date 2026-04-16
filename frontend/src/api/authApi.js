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

export async function verify2fa(sessionToken, otpCode) {
  const { data } = await apiClient.post("/auth/verify-2fa", {
    session_token: sessionToken,
    otp_code: otpCode,
  });
  return data;
}

export async function getMe() {
  const { data } = await apiClient.get("/auth/me");
  return data;
}

export async function activateAccount(token, password) {
  const { data } = await apiClient.post("/identity/activate", { token, password });
  return data;
}
