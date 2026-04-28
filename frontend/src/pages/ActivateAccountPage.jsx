import { useMemo, useState, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { activateAccount } from "../api/authApi";

const MIN_PASSWORD_LENGTH = 12;

function getPasswordStrength(password) {
  if (!password) return { level: 0, label: "", color: "" };
  const len = password.length;
  if (len < MIN_PASSWORD_LENGTH) return { level: 1, label: "Muy corta", color: "#e53e3e" };

  let score = 0;
  if (len >= 16) score++;
  if (len >= 24) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;
  if (password.includes(" ") && len >= 20) score += 2; // passphrases
  if (new Set(password.toLowerCase()).size >= 8) score++;

  if (score <= 2) return { level: 2, label: "Aceptable", color: "#dd6b20" };
  if (score <= 4) return { level: 3, label: "Buena", color: "#38a169" };
  return { level: 4, label: "Excelente", color: "#2b6cb0" };
}

function ActivateAccountPage() {
  const [params] = useSearchParams();
  const token = useMemo(() => params.get("token") || "", [params]);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [status, setStatus] = useState({ success: "", error: "" });
  const [loading, setLoading] = useState(false);

  const strength = useMemo(() => getPasswordStrength(password), [password]);

  const onSubmit = async (event) => {
    event.preventDefault();
    if (password !== confirmPassword) {
      setStatus({ success: "", error: "Las contraseñas no coinciden" });
      return;
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      setStatus({
        success: "",
        error: `La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres. Tip: usa una frase memorable.`,
      });
      return;
    }
    setLoading(true);
    setStatus({ success: "", error: "" });

    try {
      await activateAccount(token, password);
      setStatus({ success: "Cuenta activada correctamente. Ya puedes iniciar sesión.", error: "" });
      setPassword("");
      setConfirmPassword("");
    } catch (error) {
      setStatus({
        success: "",
        error: error?.response?.data?.detail || "No fue posible activar la cuenta. El token puede ser inválido o haber expirado.",
      });
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <main style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", padding: 20 }}>
        <div className="card" style={{ maxWidth: 420, width: "100%" }}>
          <h1 className="page-title">Activación de cuenta</h1>
          <div className="alert alert-error">No se encontró token de activación en la URL.</div>
          <Link to="/login" className="button button-secondary" style={{ marginTop: 12 }}>Ir a iniciar sesión</Link>
        </div>
      </main>
    );
  }

  return (
    <main style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", padding: 20 }}>
      <div className="card" style={{ maxWidth: 460, width: "100%" }}>
        <h1 className="page-title" style={{ marginBottom: 4 }}>Activar cuenta</h1>
        <p className="page-subtitle">Define una contraseña segura para finalizar tu activación.</p>

        {status.success ? (
          <>
            <div className="alert alert-success">{status.success}</div>
            <Link to="/login" className="button button-primary" style={{ width: "100%", marginTop: 8 }}>
              Ir a iniciar sesión
            </Link>
          </>
        ) : (
          <form onSubmit={onSubmit}>
            <div className="alert alert-info" style={{ marginBottom: 16, fontSize: "0.85em" }}>
              <strong>Requisitos:</strong> Mínimo {MIN_PASSWORD_LENGTH} caracteres.
              Recomendamos usar una frase memorable, por ejemplo: <em>"mi gato come tacos 42"</em>.
              No se requieren mayúsculas ni símbolos obligatorios.
            </div>

            <div className="form-group">
              <label htmlFor="password">Nueva contraseña</label>
              <input
                id="password"
                type="password"
                minLength={MIN_PASSWORD_LENGTH}
                className="input"
                placeholder="Frase o contraseña segura..."
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              {/* Strength indicator */}
              {password && (
                <div style={{ marginTop: 6 }}>
                  <div style={{
                    height: 4,
                    borderRadius: 2,
                    background: "var(--border, #333)",
                    overflow: "hidden",
                  }}>
                    <div style={{
                      height: "100%",
                      width: `${(strength.level / 4) * 100}%`,
                      background: strength.color,
                      transition: "width 0.3s, background 0.3s",
                      borderRadius: 2,
                    }} />
                  </div>
                  <p style={{ fontSize: "0.75em", color: strength.color, marginTop: 3, marginBottom: 0 }}>
                    Fortaleza: {strength.label}
                    {password.length < MIN_PASSWORD_LENGTH && ` — necesitas al menos ${MIN_PASSWORD_LENGTH - password.length} caracteres más`}
                  </p>
                </div>
              )}
            </div>
            <div className="form-group">
              <label htmlFor="confirmPassword">Confirmar contraseña</label>
              <input
                id="confirmPassword"
                type="password"
                minLength={MIN_PASSWORD_LENGTH}
                className="input"
                placeholder="Repetir contraseña"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
              {confirmPassword && password !== confirmPassword && (
                <p style={{ fontSize: "0.75em", color: "#e53e3e", marginTop: 3, marginBottom: 0 }}>
                  Las contraseñas no coinciden
                </p>
              )}
            </div>
            <button className="button button-primary" type="submit" style={{ width: "100%", marginTop: 4 }} disabled={loading}>
              {loading ? "Activando..." : "Activar cuenta"}
            </button>
          </form>
        )}
        {status.error && <div className="alert alert-error" style={{ marginTop: 12 }}>{status.error}</div>}
      </div>
    </main>
  );
}

export default ActivateAccountPage;
