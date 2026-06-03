import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { totpEnrollBegin, totpEnrollConfirm } from "../api/authApi";
import apiClient from "../api/client";
import { TOKEN_KEY } from "../constants";

function LoginPage() {
  const { verify2fa } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // 2FA state
  const [needs2fa, setNeeds2fa] = useState(false);
  const [sessionToken, setSessionToken] = useState("");
  const [otpCode, setOtpCode] = useState("");

  // TOTP enrollment state
  const [needsEnrollment, setNeedsEnrollment] = useState(false);
  const [enrollData, setEnrollData] = useState(null);
  const [enrollStep, setEnrollStep] = useState("initial"); // "initial" | "qr" | "confirm"
  const [confirmCode, setConfirmCode] = useState("");
  const [showSecret, setShowSecret] = useState(false);

  const onSubmitLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      // Manual login call (not via context) to handle pre_2fa flow
      const body = new URLSearchParams();
      body.append("username", form.email);
      body.append("password", form.password);
      const { data: response } = await apiClient.post("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      if (response.requires_2fa) {
        setSessionToken(response.session_token);

        if (response.requires_totp_enrollment) {
          // Usuario no tiene TOTP enrolado — iniciar flujo de enrolamiento
          setNeedsEnrollment(true);
          setEnrollStep("initial");
          // Temporarily set token for API calls during enrollment
          localStorage.setItem(TOKEN_KEY, response.session_token);
        } else {
          // TOTP ya enrolado — pedir código
          setNeeds2fa(true);
        }
      } else {
        navigate("/");
      }
    } catch (err) {
      setError(err?.response?.data?.detail || "No fue posible iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  const handleBeginEnroll = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await totpEnrollBegin();
      setEnrollData(data);
      setEnrollStep("qr");
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al iniciar enrolamiento TOTP");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmEnroll = async (e) => {
    e.preventDefault();
    if (confirmCode.length !== 6) return;
    setLoading(true);
    setError("");
    try {
      await totpEnrollConfirm(enrollData.secret_plain, confirmCode);
      // Enrollment OK — now complete login with the same code (or ask for a new one)
      setNeedsEnrollment(false);
      setEnrollData(null);
      setConfirmCode("");
      setEnrollStep("initial");
      // Clean up temp token
      localStorage.removeItem(TOKEN_KEY);
      // Now show normal TOTP verification
      setNeeds2fa(true);
      setOtpCode("");
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
        "Código incorrecto. Verifica que la hora de tu dispositivo esté sincronizada."
      );
    } finally {
      setLoading(false);
    }
  };

  const onSubmitOtp = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await verify2fa(sessionToken, otpCode);
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.detail || "Código TOTP inválido");
    } finally {
      setLoading(false);
    }
  };

  const onBackToLogin = () => {
    setNeeds2fa(false);
    setNeedsEnrollment(false);
    setSessionToken("");
    setOtpCode("");
    setEnrollData(null);
    setEnrollStep("initial");
    setConfirmCode("");
    setShowSecret(false);
    setError("");
    localStorage.removeItem(TOKEN_KEY);
  };

  // ─── RENDER: TOTP Enrollment ───
  if (needsEnrollment) {
    return (
      <main style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", padding: 20 }}>
        <div className="card" style={{ maxWidth: 480, width: "100%" }}>
          <div style={{ textAlign: "center", marginBottom: 20 }}>
            <img src="/casa_monarca.png" alt="Casa Monarca" style={{ height: 60, marginBottom: 8 }} />
            <h1 className="page-title" style={{ color: "var(--accent)", fontSize: "1.4em" }}>
              Configurar autenticación TOTP
            </h1>
            <p className="page-subtitle" style={{ marginBottom: 0, fontSize: "0.9em" }}>
              Para continuar debes configurar tu app autenticadora (Google Authenticator, NetIQ).
            </p>
          </div>

          {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

          {enrollStep === "initial" && (
            <div style={{ textAlign: "center" }}>
              <div className="alert alert-info" style={{ marginBottom: 16 }}>
                Tu cuenta requiere autenticación de dos factores con una app como
                <strong> Google Authenticator</strong> o <strong>NetIQ Authenticator</strong>.
                Esto agrega una capa extra de seguridad a tu cuenta.
              </div>
              <button
                className="button button-primary"
                onClick={handleBeginEnroll}
                disabled={loading}
                style={{ width: "100%" }}
              >
                {loading ? "Preparando..." : "Comenzar configuración"}
              </button>
            </div>
          )}

          {enrollStep === "qr" && enrollData && (
            <div>
              <h3 style={{ marginBottom: 8, fontSize: "1em" }}>Paso 1: Escanea el código QR</h3>
              <p style={{ fontSize: "0.85em", color: "var(--text-muted)", marginBottom: 12 }}>
                Abre tu app autenticadora y escanea este código. Si no puedes, usa la clave manual.
              </p>

              <div style={{ textAlign: "center", marginBottom: 16 }}>
                <img
                  src={enrollData.qr_data_url}
                  alt="Código QR para TOTP"
                  style={{ width: 200, height: 200, border: "1px solid var(--border)", borderRadius: 8 }}
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <button
                  type="button"
                  className="button"
                  style={{ fontSize: "0.8em", width: "100%" }}
                  onClick={() => setShowSecret(!showSecret)}
                >
                  {showSecret ? "Ocultar clave secreta" : "Mostrar clave secreta (ingreso manual)"}
                </button>
                {showSecret && (
                  <div className="alert alert-warning" style={{ marginTop: 8, fontFamily: "monospace", letterSpacing: 2, wordBreak: "break-all", fontSize: "0.9em" }}>
                    {enrollData.secret_plain}
                  </div>
                )}
              </div>

              <h3 style={{ marginBottom: 8, fontSize: "1em" }}>Paso 2: Ingresa el código de tu app</h3>
              <form onSubmit={handleConfirmEnroll}>
                <div className="form-group">
                  <input
                    id="enroll_confirm_code"
                    type="text"
                    className="input"
                    placeholder="123456"
                    maxLength={6}
                    value={confirmCode}
                    onChange={(e) => setConfirmCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    required
                    autoFocus
                    style={{ textAlign: "center", fontSize: "1.4em", letterSpacing: 8 }}
                  />
                </div>
                <button
                  className="button button-primary"
                  type="submit"
                  style={{ width: "100%" }}
                  disabled={loading || confirmCode.length !== 6}
                >
                  {loading ? "Verificando..." : "Confirmar y activar TOTP"}
                </button>
              </form>
            </div>
          )}

          <button type="button" className="button" onClick={onBackToLogin} style={{ width: "100%", marginTop: 12 }}>
            Volver al login
          </button>
        </div>
      </main>
    );
  }

  // ─── RENDER: Main login / TOTP code ───
  return (
    <main style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", padding: 20 }}>
      <div className="card" style={{ maxWidth: 420, width: "100%" }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <img src="/casa_monarca.png" alt="Casa Monarca" style={{ height: 80, marginBottom: 12 }} />
        </div>

        {!needs2fa ? (
          <form onSubmit={onSubmitLogin}>
            <div className="form-group">
              <label htmlFor="email">Correo electrónico</label>
              <input
                id="email"
                type="email"
                className="input"
                placeholder="usuario@ejemplo.org"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="password">Contraseña</label>
              <input
                id="password"
                type="password"
                className="input"
                placeholder="••••••••"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
              />
            </div>
            <button className="button button-primary" type="submit" style={{ width: "100%", marginTop: 8 }} disabled={loading}>
              {loading ? "Ingresando..." : "Iniciar sesión"}
            </button>
          </form>
        ) : (
          <form onSubmit={onSubmitOtp}>
            <div className="alert alert-info" style={{ marginBottom: 16 }}>
              Ingresa el código de 6 dígitos de tu <strong>app autenticadora</strong>
              (Google Authenticator, NetIQ, Authy).
            </div>

            <div className="form-group">
              <label htmlFor="otp_code">Código de tu app autenticadora</label>
              <input
                id="otp_code"
                type="text"
                className="input"
                placeholder="123456"
                maxLength={6}
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                required
                autoFocus
                style={{ textAlign: "center", fontSize: "1.4em", letterSpacing: 8 }}
              />
            </div>

            <button className="button button-primary" type="submit" style={{ width: "100%", marginTop: 8 }} disabled={loading || otpCode.length !== 6}>
              {loading ? "Verificando..." : "Verificar código"}
            </button>

            <button type="button" className="button" onClick={onBackToLogin} style={{ width: "100%", marginTop: 8 }}>
              Volver al login
            </button>
          </form>
        )}
        {error && <div className="alert alert-error" style={{ marginTop: 12 }}>{error}</div>}
      </div>
    </main>
  );
}

export default LoginPage;
