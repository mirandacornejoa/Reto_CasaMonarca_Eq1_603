import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
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
        error: error?.response?.data?.detail || "No fue posible activar la cuenta",
      });
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <main className="container" style={{ maxWidth: 440 }}>
        <div className="card">
          <h1>Activación</h1>
          <p className="error">No se encontró token de activación en la URL.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="container" style={{ maxWidth: 440 }}>
      <div className="card">
        <h1 style={{ marginTop: 0 }}>Activar cuenta</h1>
        <p>Define una contraseña para finalizar tu activación.</p>
        <form onSubmit={onSubmit}>
          <label htmlFor="password">Nueva contraseña (mínimo 8 caracteres)</label>
          <input
            id="password"
            type="password"
            minLength={8}
            className="input"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <label htmlFor="confirmPassword" style={{ marginTop: 10, display: "block" }}>
            Confirmar contraseña
          </label>
          <input
            id="confirmPassword"
            type="password"
            minLength={8}
            className="input"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
          />
          <button className="button" type="submit" style={{ marginTop: 12 }} disabled={loading}>
            {loading ? "Activando..." : "Activar cuenta"}
          </button>
        </form>
        {status.success ? <p className="success">{status.success}</p> : null}
        {status.error ? <p className="error">{status.error}</p> : null}
      </div>
    </main>
  );
}

export default ActivateAccountPage;
