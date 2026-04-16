import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

function LoginPage() {
  const { login, verify2fa } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // 2FA state
  const [needs2fa, setNeeds2fa] = useState(false);
  const [sessionToken, setSessionToken] = useState("");
  const [demoOtp, setDemoOtp] = useState("");
  const [otpCode, setOtpCode] = useState("");

  const onSubmitLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await login(form.email, form.password);
      if (response.requires_2fa) {
        setNeeds2fa(true);
        setSessionToken(response.session_token);
        setDemoOtp(response.demo_otp || "");
      } else {
        navigate("/");
      }
    } catch (err) {
      setError(err?.response?.data?.detail || "No fue posible iniciar sesion");
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
      setError(err?.response?.data?.detail || "Codigo de verificacion invalido");
    } finally {
      setLoading(false);
    }
  };

  const onBackToLogin = () => {
    setNeeds2fa(false);
    setSessionToken("");
    setDemoOtp("");
    setOtpCode("");
    setError("");
  };

  return (
    <main style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", padding: 20 }}>
      <div className="card" style={{ maxWidth: 420, width: "100%" }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <h1 className="page-title" style={{ background: "linear-gradient(135deg, var(--accent), var(--purple))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Casa Monarca
          </h1>
          <p className="page-subtitle" style={{ marginBottom: 0 }}>Gestor de Identidades y Control de Acceso</p>
        </div>

        {!needs2fa ? (
          <form onSubmit={onSubmitLogin}>
            <div className="form-group">
              <label htmlFor="email">Correo electronico</label>
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
              <label htmlFor="password">Contrasena</label>
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
              {loading ? "Ingresando..." : "Iniciar sesion"}
            </button>
          </form>
        ) : (
          <form onSubmit={onSubmitOtp}>
            <div className="alert alert-info" style={{ marginBottom: 16 }}>
              Se envio un codigo de verificacion a <strong>{form.email}</strong>.
              Ingresalo para completar el inicio de sesion.
            </div>

            {demoOtp && (
              <div className="alert alert-warning" style={{ marginBottom: 16 }}>
                <strong>Modo demo:</strong> tu codigo OTP es <code style={{ fontSize: "1.15em", letterSpacing: 2 }}>{demoOtp}</code>
              </div>
            )}

            <div className="form-group">
              <label htmlFor="otp_code">Codigo de verificacion (6 digitos)</label>
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
              {loading ? "Verificando..." : "Verificar codigo"}
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
