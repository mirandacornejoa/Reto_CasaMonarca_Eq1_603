import { useMemo, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { activateAccount } from "../api/authApi";

function ActivateAccountPage() {
  const [params] = useSearchParams();
  const token = useMemo(() => params.get("token") || "", [params]);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [status, setStatus] = useState({ success: "", error: "" });
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event) => {
    event.preventDefault();
    if (password !== confirmPassword) {
      setStatus({ success: "", error: "Las contraseñas no coinciden" });
      return;
    }
    if (password.length < 8) {
      setStatus({ success: "", error: "La contraseña debe tener al menos 8 caracteres" });
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
      <div className="card" style={{ maxWidth: 420, width: "100%" }}>
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
            <div className="form-group">
              <label htmlFor="password">Nueva contraseña (mínimo 8 caracteres)</label>
              <input
                id="password"
                type="password"
                minLength={8}
                className="input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="confirmPassword">Confirmar contraseña</label>
              <input
                id="confirmPassword"
                type="password"
                minLength={8}
                className="input"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
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
