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

// ── TOTP ──────────────────────────────────────────────────────────

export async function totpStatus() {
  const { data } = await apiClient.get("/auth/totp/status");
  return data;
}

export async function totpEnrollBegin() {
  const { data } = await apiClient.post("/auth/totp/enroll/begin");
  return data;
}

export async function totpEnrollConfirm(secretPlain, totpCode) {
  const { data } = await apiClient.post("/auth/totp/enroll/confirm", {
    secret_plain: secretPlain,
    totp_code: totpCode,
  });
  return data;
}

export async function totpRevoke(userId) {
  const { data } = await apiClient.delete(`/auth/totp/revoke/${userId}`);
  return data;
}

// ── Firma documental — Modelo SAT ──────────────────────────────────

export async function signingStatus() {
  const { data } = await apiClient.get("/auth/signing/status");
  return data;
}

export async function signingEnroll(keyPassword, years = 1) {
  const { data } = await apiClient.post("/auth/signing/enroll", {
    key_password: keyPassword,
    years,
  });
  return data;
}

export async function signingDownloadCertificate() {
  const { data } = await apiClient.get("/auth/signing/certificate/download");
  return data;
}

export async function signingVerify(resourceType, resourceId, contentHash, signatureB64) {
  const { data } = await apiClient.post("/auth/signing/verify", {
    resource_type: resourceType,
    resource_id: resourceId,
    content_hash: contentHash,
    signature_b64: signatureB64,
  });
  return data;
}

export async function signingRevoke(userId) {
  const { data } = await apiClient.delete(`/auth/signing/revoke/${userId}`);
  return data;
}
