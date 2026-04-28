import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { totpStatus, totpEnrollBegin, totpEnrollConfirm } from "../api/authApi";

/**
 * Página de enrolamiento TOTP.
 * Flujo:
 *   1. Muestra el estado actual (enrolado / no enrolado)
 *   2. Inicia enrolamiento → muestra QR + secreto manual
 *   3. Usuario ingresa código de confirmación de su app
 *   4. Backend confirma → TOTP activo
 */
function TOTPSetupPage() {
  const navigate = useNavigate();

  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Datos de enrolamiento
  const [enrollData, setEnrollData] = useState(null);
  const [confirmCode, setConfirmCode] = useState("");
  const [confirming, setConfirming] = useState(false);

  const [showSecret, setShowSecret] = useState(false);

  useEffect(() => {
    totpStatus()
      .then(setStatus)
      .catch(() => setError("Error al consultar estado TOTP"))
      .finally(() => setLoading(false));
  }, []);

  const handleBeginEnroll = async () => {
    setError("");
    setLoading(true);
    try {
      const data = await totpEnrollBegin();
      setEnrollData(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al iniciar enrolamiento");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmEnroll = async (e) => {
    e.preventDefault();
    if (confirmCode.length !== 6) return;
    setConfirming(true);
    setError("");
    try {
      await totpEnrollConfirm(enrollData.secret_plain, confirmCode);
      setSuccess("TOTP configurado correctamente. Desde ahora usaras tu app autenticadora para iniciar sesion.");
      setEnrollData(null);
      setConfirmCode("");
      const updated = await totpStatus();
      setStatus(updated);
    } catch (err) {
      setError(err?.response?.data?.detail || "Codigo incorrecto. Verifica que la hora de tu dispositivo este sincronizada.");
    } finally {
      setConfirming(false);
    }
  };

  if (loading) {
    return (
      <main style={{ display: "flex", justifyContent: "center", padding: 40 }}>
        <p>Cargando...</p>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 560, margin: "0 auto", padding: "40px 20px" }}>
      <h1 className="page-title">Configurar autenticacion de dos factores (TOTP)</h1>
      <p className="page-subtitle">
        Configura tu app autenticadora (Google Authenticator, NetIQ, Authy) para mayor seguridad.
      </p>

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}
      {success && <div className="alert alert-success" style={{ marginBottom: 16 }}>{success}</div>}

      {/* Estado actual */}
      {status && !enrollData && (
        <div className="card" style={{ marginBottom: 24 }}>
          <p>
            <strong>Estado:</strong>{" "}
            {status.totp_enrolled ? (
              <span style={{ color: "var(--success, green)" }}>TOTP activo</span>
            ) : (
              <span style={{ color: "var(--warning, orange)" }}>No configurado</span>
            )}
          </p>
          {status.totp_enrolled_at && (
            <p><small>Configurado el: {new Date(status.totp_enrolled_at).toLocaleString()}</small></p>
          )}

          {!status.totp_enrolled && (
            <button className="button button-primary" onClick={handleBeginEnroll} disabled={loading}>
              Configurar TOTP ahora
            </button>
          )}

          {status.totp_enrolled && (
            <button className="button" onClick={handleBeginEnroll} style={{ marginTop: 8 }}>
              Reconfigurar TOTP (nuevo dispositivo)
            </button>
          )}
        </div>
      )}

      {/* Flujo de enrolamiento */}
      {enrollData && (
        <div className="card">
          <h2 style={{ marginBottom: 12 }}>Paso 1: Escanea el codigo QR</h2>
          <p style={{ marginBottom: 12 }}>
            Abre tu app autenticadora y escanea este codigo QR. Si no puedes escanear,
            usa la clave secreta manual.
          </p>

          <div style={{ textAlign: "center", marginBottom: 16 }}>
            <img
              src={enrollData.qr_data_url}
              alt="Codigo QR para TOTP"
              style={{ width: 200, height: 200, border: "1px solid #ccc", borderRadius: 4 }}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <button
              type="button"
              className="button"
              style={{ fontSize: "0.85em" }}
              onClick={() => setShowSecret(!showSecret)}
            >
              {showSecret ? "Ocultar clave secreta" : "Mostrar clave secreta (ingreso manual)"}
            </button>
            {showSecret && (
              <div className="alert alert-warning" style={{ marginTop: 8, fontFamily: "monospace", letterSpacing: 2 }}>
                {enrollData.secret_plain}
              </div>
            )}
          </div>

          <h2 style={{ marginBottom: 12 }}>Paso 2: Confirma con un codigo</h2>
          <p style={{ marginBottom: 8 }}>
            Ingresa el codigo de 6 digitos que muestra tu app para confirmar la configuracion.
          </p>

          <form onSubmit={handleConfirmEnroll}>
            <div className="form-group">
              <label htmlFor="confirm_code">Codigo de tu app autenticadora</label>
              <input
                id="confirm_code"
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
              disabled={confirming || confirmCode.length !== 6}
            >
              {confirming ? "Verificando..." : "Confirmar enrolamiento"}
            </button>

            <button
              type="button"
              className="button"
              style={{ width: "100%", marginTop: 8 }}
              onClick={() => { setEnrollData(null); setConfirmCode(""); setError(""); }}
            >
              Cancelar
            </button>
          </form>
        </div>
      )}

      <div style={{ marginTop: 24 }}>
        <button className="button" onClick={() => navigate("/")}>
          Volver al inicio
        </button>
      </div>
    </main>
  );
}

export default TOTPSetupPage;
