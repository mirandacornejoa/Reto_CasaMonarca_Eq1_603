import { useState } from "react";
import { signContent } from "../utils/webCrypto";

/**
 * Panel reutilizable de firma digital.
 *
 * Props:
 *   canonicalContent  — string canónico a firmar (producido por buildCanonicalContent)
 *   onSigned          — callback({ contentHash, signatureB64 }) cuando se firma correctamente
 *   signed            — bool, si ya está firmado muestra estado de éxito
 */
function SignaturePanel({ canonicalContent, onSigned, signed }) {
  const [keyContent, setKeyContent] = useState("");
  const [password, setPassword] = useState("");
  const [signing, setSigning] = useState(false);
  const [signError, setSignError] = useState("");

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setSignError("");
    const reader = new FileReader();
    reader.onload = (ev) => setKeyContent(ev.target.result);
    reader.readAsText(file);
  };

  const handleSign = async () => {
    if (!keyContent) { setSignError("Selecciona tu archivo de clave privada (.key)."); return; }
    if (!password) { setSignError("Ingresa la contraseña de tu archivo .key."); return; }
    setSigning(true);
    setSignError("");
    try {
      const { contentHash, signatureB64 } = await signContent(canonicalContent, keyContent, password);
      setPassword("");
      onSigned({ contentHash, signatureB64 });
    } catch (err) {
      setSignError(err.message || "Error al firmar. Verifica que el archivo y la contraseña sean correctos.");
    } finally {
      setSigning(false);
    }
  };

  if (signed) {
    return (
      <div className="alert alert-success" style={{ fontSize: 13, marginTop: 8 }}>
        Firmado con certificado digital — puedes confirmar la acción.
      </div>
    );
  }

  return (
    <div style={{
      border: "1px solid var(--border)",
      borderRadius: 8,
      padding: "12px 14px",
      marginTop: 12,
      background: "var(--bg-secondary)",
    }}>
      <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: "var(--text-secondary)" }}>
        Firma digital requerida
      </p>
      <p style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 10 }}>
        Esta acción requiere tu certificado de firma. Sube tu archivo <code>.key</code> e ingresa tu contraseña.
        La clave privada solo se usa en este momento y no se guarda.
      </p>

      <div className="form-group" style={{ marginBottom: 8 }}>
        <label style={{ fontSize: 12 }}>Archivo de clave privada (.key)</label>
        <input
          type="file"
          accept=".key"
          onChange={handleFileChange}
          className="input"
          style={{ fontSize: 12, padding: "6px 8px" }}
        />
        {keyContent && (
          <span style={{ fontSize: 11, color: "var(--accent)", marginTop: 2, display: "block" }}>
            Archivo cargado
          </span>
        )}
      </div>

      <div className="form-group" style={{ marginBottom: 10 }}>
        <label style={{ fontSize: 12 }}>Contraseña del archivo .key</label>
        <input
          type="password"
          className="input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSign()}
          placeholder="Contraseña de tu clave privada"
          style={{ fontSize: 12 }}
          autoComplete="off"
        />
      </div>

      {signError && (
        <div className="alert alert-error" style={{ fontSize: 12, marginBottom: 8 }}>
          {signError}
        </div>
      )}

      <button
        type="button"
        className="button button-primary button-sm"
        onClick={handleSign}
        disabled={signing || !keyContent}
      >
        {signing ? "Firmando..." : "Firmar acción"}
      </button>
    </div>
  );
}

export default SignaturePanel;
