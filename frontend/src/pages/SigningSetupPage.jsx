import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { signingStatus, signingEnroll, signingDownloadCertificate } from "../api/authApi";
import { downloadAsFile } from "../utils/webCrypto";

/**
 * Página de enrolamiento de firma documental — Modelo SAT.
 *
 * Flujo:
 *   1. El usuario define una contraseña para proteger su clave privada
 *   2. El backend genera el par de claves ECDSA P-256
 *   3. El backend crea un certificado X.509 autofirmado (.cer)
 *   4. El backend cifra la clave privada con la contraseña (.key)
 *   5. Se descargan ambos archivos UNA SOLA VEZ
 *   6. El usuario debe guardarlos en un lugar seguro
 *
 * Para firmar: el usuario sube su .key + contraseña en cada firma.
 * La clave privada NO se guarda en el navegador ni en el backend.
 */
function SigningSetupPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [certStatus, setCertStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [enrolling, setEnrolling] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Password modal state
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [keyPassword, setKeyPassword] = useState("");
  const [keyPasswordConfirm, setKeyPasswordConfirm] = useState("");

  // Reset ALL state when user changes — prevents cross-user contamination
  useEffect(() => {
    let cancelled = false;

    // Immediately clear stale state from previous user
    setCertStatus(null);
    setError("");
    setSuccess("");
    setShowPasswordModal(false);
    setKeyPassword("");
    setKeyPasswordConfirm("");
    setLoading(true);

    const fetchStatus = async () => {
      try {
        const status = await signingStatus();
        if (!cancelled) setCertStatus(status);
      } catch {
        if (!cancelled) setError("Error al consultar estado de firma");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    if (user?.id) {
      fetchStatus();
    } else {
      setLoading(false);
    }

    return () => { cancelled = true; };
  }, [user?.id]);

  // ── Generar nuevo certificado ──

  const handleStartEnroll = () => {
    setKeyPassword("");
    setKeyPasswordConfirm("");
    setShowPasswordModal(true);
    setError("");
    setSuccess("");
  };

  const handleEnrollWithPassword = async () => {
    if (keyPassword.length < 8) {
      setError("La contraseña del archivo debe tener al menos 8 caracteres.");
      return;
    }
    if (keyPassword !== keyPasswordConfirm) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setEnrolling(true);
    setError("");
    setShowPasswordModal(false);
    try {
      // El backend genera todo: certificado X.509 + clave privada cifrada
      const result = await signingEnroll(keyPassword);

      // Descargar ambos archivos — DESCARGA ÚNICA
      downloadAsFile(result.cer_pem, `${user?.email || "firma"}_certificado.cer`);

      // Pequeña pausa para que el navegador no bloquee la segunda descarga
      await new Promise((r) => setTimeout(r, 500));
      downloadAsFile(result.key_pem, `${user?.email || "firma"}_clave_privada.key`);

      setCertStatus(result.certificate);
      setSuccess(
        "✅ Certificado de firma generado exitosamente.\n\n" +
        "Se han descargado DOS archivos:\n" +
        "📄 .cer — Tu certificado público\n" +
        "🔑 .key — Tu clave privada (protegida con tu contraseña)\n\n" +
        "⚠️ Guarda ambos archivos en un lugar seguro. " +
        "La clave privada NO se puede recuperar — este es tu único momento de descargarla."
      );
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Error al generar certificado de firma");
    } finally {
      setEnrolling(false);
      setKeyPassword("");
      setKeyPasswordConfirm("");
    }
  };

  const handleReenroll = async () => {
    if (!window.confirm(
      "Al generar nuevas claves, el certificado anterior quedará revocado y necesitarás los nuevos archivos .cer y .key para firmar. ¿Continuar?"
    )) return;
    handleStartEnroll();
  };

  const handleDownloadCer = async () => {
    setError("");
    try {
      const result = await signingDownloadCertificate();
      downloadAsFile(result.cer_pem, `${user?.email || "firma"}_certificado.cer`);
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al descargar certificado");
    }
  };

  if (loading) {
    return (
      <main style={{ display: "flex", justifyContent: "center", padding: 40 }}>
        <p>Cargando...</p>
      </main>
    );
  }

  const certValid = certStatus?.has_signing_cert && certStatus?.status === "VALID";

  return (
    <main style={{ maxWidth: 580, margin: "0 auto", padding: "40px 20px" }}>
      <h1 className="page-title">Configurar firma documental</h1>
      <p className="page-subtitle">
        Tu certificado de firma se genera en el servidor. Recibirás dos archivos:
        un certificado público (.cer) y una clave privada cifrada (.key).
        Para firmar documentos necesitarás tu archivo .key y tu contraseña.
      </p>

      {error && <div className="alert alert-error" style={{ marginBottom: 16, whiteSpace: "pre-line" }}>{error}</div>}
      {success && <div className="alert alert-success" style={{ marginBottom: 16, whiteSpace: "pre-line" }}>{success}</div>}

      {/* Password Modal */}
      {showPasswordModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center",
          justifyContent: "center", zIndex: 1000,
        }}>
          <div className="card" style={{ maxWidth: 420, width: "90%", margin: 20 }}>
            <h3 style={{ marginBottom: 12 }}>
              Crear contraseña para clave privada
            </h3>

            <div className="form-group">
              <label>Contraseña para proteger tu clave privada</label>
              <input
                type="password"
                className="input"
                placeholder="Mínimo 8 caracteres"
                value={keyPassword}
                onChange={(e) => setKeyPassword(e.target.value)}
                autoFocus
              />
            </div>

            <div className="form-group">
              <label>Confirmar contraseña</label>
              <input
                type="password"
                className="input"
                placeholder="Repetir contraseña"
                value={keyPasswordConfirm}
                onChange={(e) => setKeyPasswordConfirm(e.target.value)}
              />
            </div>

            <div className="alert alert-info" style={{ fontSize: "0.8em", marginBottom: 12 }}>
              Esta contraseña protege tu archivo de clave privada. <strong>No</strong> es tu contraseña de login.
              La necesitarás cada vez que firmes un documento. <strong>Guárdala en un lugar seguro.</strong>
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="button button-primary"
                style={{ flex: 1 }}
                onClick={handleEnrollWithPassword}
                disabled={enrolling}
              >
                {enrolling ? "Generando..." : "Generar y descargar"}
              </button>
              <button
                className="button"
                onClick={() => { setShowPasswordModal(false); setKeyPassword(""); setKeyPasswordConfirm(""); }}
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cert Status */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ marginBottom: 12 }}>Estado del certificado de firma</h3>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <tbody>
            <tr>
              <td style={{ padding: "4px 0", color: "#888" }}>Certificado</td>
              <td>
                {certValid ? (
                  <span style={{ color: "green" }}>✅ Activo</span>
                ) : certStatus?.has_signing_cert ? (
                  <span style={{ color: "red" }}>❌ Revocado/Expirado</span>
                ) : (
                  <span style={{ color: "orange" }}>⚠ No registrado</span>
                )}
              </td>
            </tr>
            {certStatus?.serial_number && (
              <tr>
                <td style={{ padding: "4px 0", color: "#888" }}>Serial</td>
                <td><code style={{ fontSize: "0.8em" }}>{certStatus.serial_number.substring(0, 16)}...</code></td>
              </tr>
            )}
            {certStatus?.fingerprint && (
              <tr>
                <td style={{ padding: "4px 0", color: "#888" }}>Huella digital</td>
                <td><code style={{ fontSize: "0.8em" }}>{certStatus.fingerprint.substring(0, 16)}...</code></td>
              </tr>
            )}
            {certStatus?.expires_at && (
              <tr>
                <td style={{ padding: "4px 0", color: "#888" }}>Vigencia</td>
                <td>{new Date(certStatus.expires_at).toLocaleDateString()}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* How it works */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ marginBottom: 8 }}>¿Cómo funciona?</h3>
        <ol style={{ fontSize: "0.85em", color: "var(--text-muted)", paddingLeft: 20, margin: 0 }}>
          <li style={{ marginBottom: 6 }}><strong>Generas tu certificado</strong> → se descargan dos archivos: <code>.cer</code> (público) y <code>.key</code> (privado, cifrado con tu contraseña)</li>
          <li style={{ marginBottom: 6 }}><strong>Guardas ambos archivos</strong> en un lugar seguro (USB, carpeta personal, etc.)</li>
          <li style={{ marginBottom: 6 }}><strong>Para firmar</strong> → subes tu archivo <code>.key</code> e ingresas tu contraseña</li>
          <li><strong>La clave privada nunca se guarda</strong> en el navegador ni en el servidor — solo se usa en el momento de firmar</li>
        </ol>
      </div>

      {/* Actions */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        {!certValid && (
          <button
            className="button button-primary"
            onClick={handleStartEnroll}
            disabled={enrolling}
          >
            {enrolling ? "Generando certificado..." : "Generar certificado de firma"}
          </button>
        )}

        {certValid && (
          <>
            <div className="alert alert-success" style={{ width: "100%", marginBottom: 8 }}>
              Tu firma digital está lista. Ve a <strong>Registros</strong> para firmar expedientes
              usando tu archivo .key y contraseña.
            </div>
            <button className="button" onClick={handleDownloadCer} disabled={enrolling}>
              📄 Descargar certificado público (.cer)
            </button>
            <button className="button" onClick={handleReenroll} disabled={enrolling}>
              🔄 Generar nuevas claves
            </button>
          </>
        )}
      </div>

      <div style={{ marginTop: 24 }}>
        <button className="button" onClick={() => navigate("/")}>
          Volver al inicio
        </button>
      </div>
    </main>
  );
}

export default SigningSetupPage;
