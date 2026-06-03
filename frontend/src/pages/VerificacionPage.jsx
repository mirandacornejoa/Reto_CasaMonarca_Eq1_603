import { useEffect, useState } from "react";
import AppNav from "../components/AppNav";
import { useAuth } from "../hooks/useAuth";
import { listArcoRequests } from "../api/arcoApi";
import { listDeletionRequests } from "../api/deletionRequestsApi";
import { getSignatureStatus, verifySignature } from "../api/signaturesApi";

const ARCO_TYPE_LABELS = {
  ACCESS: "Acceso",
  RECTIFICATION: "Rectificación",
  CANCELLATION: "Cancelación",
  OPPOSITION: "Oposición",
};

const ARCO_STATUS_LABELS = {
  COMPLETED: "Completada",
  APPROVED: "Aprobada",
  REJECTED: "Rechazada",
};

const DEL_STATUS_LABELS = {
  approved: "Aprobada",
  rejected: "Rechazada",
};

function VerificacionPage() {
  const { user } = useAuth();
  const level = user?.access_level_code;

  const [arcoItems, setArcoItems] = useState([]);
  const [delItems, setDelItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Estado expandido por item: { "arco-5": { loading, data, verifyResult, verifyLoading } }
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      setError("");
      try {
        const arco = await listArcoRequests();
        setArcoItems(arco.filter((r) => ["COMPLETED", "APPROVED", "REJECTED"].includes(r.status)));

        if (level <= 2) {
          const del = await listDeletionRequests();
          setDelItems(del.filter((r) => r.status !== "pending"));
        }
      } catch (err) {
        const d = err?.response?.data?.detail;
        setError(typeof d === "string" ? d : "Error cargando solicitudes");
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, [level]);

  const toggleExpand = async (key, resourceType, resourceId) => {
    // Si ya está expandido, colapsar
    if (expanded[key]?.open) {
      setExpanded((prev) => ({ ...prev, [key]: { ...prev[key], open: false } }));
      return;
    }

    // Abrir y cargar si no se ha cargado aún
    if (expanded[key]?.data) {
      setExpanded((prev) => ({ ...prev, [key]: { ...prev[key], open: true } }));
      return;
    }

    setExpanded((prev) => ({ ...prev, [key]: { open: true, loading: true, data: null, verifyResult: null, verifyLoading: false } }));
    try {
      const data = await getSignatureStatus(resourceType, resourceId);
      setExpanded((prev) => ({ ...prev, [key]: { ...prev[key], loading: false, data } }));
    } catch {
      setExpanded((prev) => ({ ...prev, [key]: { ...prev[key], loading: false, data: { signed: false } } }));
    }
  };

  const doVerify = async (key, resourceType, resourceId) => {
    setExpanded((prev) => ({ ...prev, [key]: { ...prev[key], verifyLoading: true, verifyResult: null } }));
    try {
      const result = await verifySignature(resourceType, resourceId);
      setExpanded((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          verifyLoading: false,
          verifyResult: result,
          // Actualizar last_verification_result en data
          data: { ...prev[key].data, last_verification_result: result.valid ? "VALID" : "INVALID" },
        },
      }));
    } catch (err) {
      const d = err?.response?.data?.detail;
      setExpanded((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          verifyLoading: false,
          verifyResult: { valid: false, message: typeof d === "string" ? d : "Error al verificar" },
        },
      }));
    }
  };

  const fmtDate = (d) =>
    d ? new Date(d).toLocaleString("es-MX", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

  const totalItems = arcoItems.length + delItems.length;

  return (
    <main className="container">
      <AppNav />

      <h1 className="page-title">Verificación de firmas digitales</h1>
      <p className="page-subtitle">
        Consulta y verifica las firmas de las resoluciones que te involucran.
        Los certificados públicos de los firmantes están disponibles para cualquier nivel.
      </p>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <p className="loading">Cargando resoluciones...</p>
      ) : totalItems === 0 ? (
        <div className="card">
          <div className="empty-state">
            <p>No hay resoluciones firmadas disponibles aún.</p>
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
              Las resoluciones aparecerán aquí una vez que tus solicitudes ARCO sean atendidas.
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* ── Solicitudes ARCO resueltas ── */}
          {arcoItems.length > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <h3 className="section-title">Solicitudes ARCO resueltas ({arcoItems.length})</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                {arcoItems.map((req) => {
                  const key = `arco-${req.id}`;
                  const ex = expanded[key];
                  return (
                    <SignatureRow
                      key={key}
                      folio={req.folio || `ARCO-${req.id}`}
                      typeLabel={ARCO_TYPE_LABELS[req.request_type] || req.request_type}
                      statusLabel={ARCO_STATUS_LABELS[req.status] || req.status}
                      statusClass={req.status === "APPROVED" ? "badge-active" : req.status === "COMPLETED" ? "badge-valid" : "badge-revoked"}
                      date={req.resolved_at || req.updated_at}
                      fmtDate={fmtDate}
                      expanded={ex}
                      onToggle={() => toggleExpand(key, "arco_request", req.id)}
                      onVerify={() => doVerify(key, "arco_request", req.id)}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {/* ── Peticiones de eliminación resueltas (nivel 2+) ── */}
          {delItems.length > 0 && (
            <div className="card">
              <h3 className="section-title">Peticiones de eliminación resueltas ({delItems.length})</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                {delItems.map((req) => {
                  const key = `del-${req.id}`;
                  const ex = expanded[key];
                  return (
                    <SignatureRow
                      key={key}
                      folio={req.folio || `DEL-${req.id}`}
                      typeLabel={`Eliminación — ${req.record_folio || `Registro #${req.record_id}`}`}
                      statusLabel={DEL_STATUS_LABELS[req.status] || req.status}
                      statusClass={req.status === "approved" ? "badge-active" : "badge-revoked"}
                      date={req.reviewed_at}
                      fmtDate={fmtDate}
                      expanded={ex}
                      onToggle={() => toggleExpand(key, "deletion_request", req.id)}
                      onVerify={() => doVerify(key, "deletion_request", req.id)}
                    />
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* Nota informativa */}
      <div className="card" style={{ marginTop: 16, background: "var(--bg-secondary)" }}>
        <p style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6, margin: 0 }}>
          <strong>Sobre la verificación:</strong> El sistema usa firma digital ECDSA P-256 (equivalente al modelo SAT).
          Cada resolución es firmada con la clave privada del coordinador o administrador responsable.
          Al verificar, el servidor compara la firma almacenada contra la clave pública del certificado del firmante.
          La clave pública mostrada aquí es la misma que el firmante registró al generar su certificado.
        </p>
      </div>
    </main>
  );
}

// ── Fila expandible de firma ──────────────────────────────────────────
function SignatureRow({ folio, typeLabel, statusLabel, statusClass, date, fmtDate, expanded, onToggle, onVerify }) {
  const ex = expanded;
  const isOpen = ex?.open;

  return (
    <div style={{ borderBottom: "1px solid var(--border)" }}>
      {/* Cabecera del item */}
      <div
        style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 4px", cursor: "pointer" }}
        onClick={onToggle}
      >
        <span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 600, color: "var(--accent)", minWidth: 120 }}>
          {folio}
        </span>
        <span style={{ fontSize: 13, flex: 1 }}>{typeLabel}</span>
        <span className={`badge ${statusClass}`} style={{ fontSize: 11 }}>{statusLabel}</span>
        <span style={{ fontSize: 11, color: "var(--text-muted)", minWidth: 120, textAlign: "right" }}>
          {fmtDate(date)}
        </span>
        <span style={{ fontSize: 12, color: "var(--accent)", minWidth: 80, textAlign: "right" }}>
          {isOpen ? "▲ Ocultar" : "▼ Ver firma"}
        </span>
      </div>

      {/* Panel expandido */}
      {isOpen && (
        <div style={{ padding: "12px 4px 20px 4px", borderTop: "1px dashed var(--border)" }}>
          {ex.loading ? (
            <p style={{ color: "var(--text-muted)", fontSize: 13 }}>Cargando información de firma...</p>
          ) : !ex.data?.signed ? (
            <div className="alert alert-warning" style={{ fontSize: 13 }}>
              Esta resolución no tiene firma digital registrada. Fue procesada antes de que se implementara la firma obligatoria.
            </div>
          ) : (
            <div>
              <div className="alert alert-success" style={{ fontSize: 13, marginBottom: 14 }}>
                Resolución firmada digitalmente con certificado ECDSA P-256.
              </div>

              {/* Datos del firmante */}
              <div style={{ display: "grid", gridTemplateColumns: "160px 1fr", gap: "6px 12px", fontSize: 13, marginBottom: 16 }}>
                <span style={{ color: "var(--text-muted)" }}>Firmado por</span>
                <span>
                  <strong>{ex.data.signer_name}</strong>
                  {ex.data.signer_matricula && (
                    <span style={{ color: "var(--text-muted)", fontSize: 11 }}> · {ex.data.signer_matricula}</span>
                  )}
                </span>

                <span style={{ color: "var(--text-muted)" }}>Fecha de firma</span>
                <span>{fmtDate(ex.data.signed_at)}</span>

                <span style={{ color: "var(--text-muted)" }}>Algoritmo</span>
                <span><code style={{ fontSize: 11 }}>{ex.data.algorithm}</code></span>

                {ex.data.certificate_serial && (
                  <>
                    <span style={{ color: "var(--text-muted)" }}>Nº de serie</span>
                    <span><code style={{ fontSize: 10, wordBreak: "break-all" }}>{ex.data.certificate_serial.slice(0, 32)}…</code></span>
                  </>
                )}

                <span style={{ color: "var(--text-muted)" }}>Huella digital</span>
                <span>
                  <code style={{ fontSize: 10, wordBreak: "break-all", display: "block", maxWidth: 480 }}>
                    {ex.data.fingerprint}
                  </code>
                </span>

                <span style={{ color: "var(--text-muted)" }}>Última verificación</span>
                <span>
                  {ex.data.last_verification_result === "VALID"
                    ? <span style={{ color: "#16a34a", fontWeight: 600 }}>Válida</span>
                    : ex.data.last_verification_result === "INVALID"
                    ? <span style={{ color: "#dc2626", fontWeight: 600 }}>Inválida</span>
                    : <span style={{ color: "var(--text-muted)" }}>Sin verificar</span>}
                </span>
              </div>

              {/* Clave pública */}
              {ex.data.public_key_pem ? (
                <div style={{ marginBottom: 14 }}>
                  <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 6 }}>
                    Clave pública del firmante (SPKI / PEM):
                  </p>
                  <div style={{ position: "relative" }}>
                    <pre style={{
                      background: "var(--bg-secondary)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "10px 12px",
                      fontSize: 10,
                      fontFamily: "monospace",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-all",
                      color: "var(--text-secondary)",
                      maxHeight: 180,
                      overflowY: "auto",
                      margin: 0,
                    }}>
                      {ex.data.public_key_pem}
                    </pre>
                    <button
                      type="button"
                      className="button button-ghost button-sm"
                      style={{ position: "absolute", top: 6, right: 6, fontSize: 10, padding: "2px 8px" }}
                      onClick={() => {
                        navigator.clipboard?.writeText(ex.data.public_key_pem);
                      }}
                      title="Copiar clave pública"
                    >
                      Copiar
                    </button>
                  </div>
                  <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                    Esta es la clave pública registrada en el sistema para este firmante. Puedes usarla para verificar la firma de forma independiente con cualquier herramienta compatible con ECDSA P-256.
                  </p>
                </div>
              ) : (
                <div className="alert alert-warning" style={{ fontSize: 12, marginBottom: 14 }}>
                  Clave pública no disponible en el certificado almacenado.
                </div>
              )}

              {/* Resultado de verificación */}
              {ex.verifyResult && (
                <div
                  className={`alert ${ex.verifyResult.valid ? "alert-success" : "alert-error"}`}
                  style={{ fontSize: 13, marginBottom: 12 }}
                >
                  {ex.verifyResult.valid ? "✓ " : "✕ "}{ex.verifyResult.message}
                </div>
              )}

              {/* Botón verificar */}
              <button
                type="button"
                className="button button-primary button-sm"
                onClick={onVerify}
                disabled={ex.verifyLoading}
              >
                {ex.verifyLoading ? "Verificando..." : "Verificar firma ahora"}
              </button>
              <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 10 }}>
                El servidor comprueba la firma ECDSA contra la clave pública del certificado del firmante.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default VerificacionPage;
