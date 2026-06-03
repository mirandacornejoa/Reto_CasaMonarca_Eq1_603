import { useEffect, useState } from "react";
import AppNav from "../components/AppNav";
import SignaturePanel from "../components/SignaturePanel";
import { useAuth } from "../hooks/useAuth";
import {
  listArcoRequests,
  attendArcoRequest,
  escalateArcoRequest,
  reviewArcoRequest,
} from "../api/arcoApi";
import { verifyCertSignature } from "../api/signaturesApi";
import { buildCanonicalContent } from "../utils/webCrypto";

function extractApiError(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => e.msg || String(e)).join(" · ");
  return fallback;
}

const STATUS_LABELS = {
  PENDING: "Pendiente",
  IN_REVIEW: "En revisión",
  ESCALATED: "Escalada",
  COMPLETED: "Completada",
  APPROVED: "Aprobada",
  REJECTED: "Rechazada",
};

const TYPE_LABELS = {
  ACCESS: "Acceso",
  RECTIFICATION: "Rectificación",
  CANCELLATION: "Cancelación",
  OPPOSITION: "Oposición",
};

const STATUS_BADGE = {
  PENDING: "badge-pending",
  IN_REVIEW: "badge-warning",
  ESCALATED: "badge-inactive",
  COMPLETED: "badge-valid",
  APPROVED: "badge-active",
  REJECTED: "badge-revoked",
};

const RESOLVED_STATUSES = ["COMPLETED", "APPROVED", "REJECTED"];

/** Devuelve el nombre de quien resolvió una solicitud ARCO. */
function resolvedByName(req) {
  if (req.status === "COMPLETED") return req.assigned_coordinator_name || null;
  if (req.status === "APPROVED" || req.status === "REJECTED") return req.assigned_admin_name || null;
  return null;
}

function ArcoPage() {
  const { user } = useAuth();
  const level = user?.access_level_code;

  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Modal de acción (attend / escalate / approve / reject)
  const [actionReq, setActionReq] = useState(null);
  const [actionType, setActionType] = useState("");
  const [notes, setNotes] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [signatureData, setSignatureData] = useState(null);

  // Modal de verificación con .cer
  const [certModal, setCertModal] = useState(null); // { req }
  const [certContent, setCertContent] = useState("");
  const [certFileName, setCertFileName] = useState("");
  const [certVerifyLoading, setCertVerifyLoading] = useState(false);
  const [certVerifyResult, setCertVerifyResult] = useState(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listArcoRequests();
      setRequests(data);
    } catch (err) {
      setError(extractApiError(err, "Error cargando solicitudes ARCO"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openAction = (req, type) => {
    setActionReq(req);
    setActionType(type);
    setNotes("");
    setSignatureData(null);
    setError("");
    setSuccess("");
  };

  const closeAction = () => {
    setActionReq(null);
    setActionType("");
    setNotes("");
    setSignatureData(null);
  };

  const openCertModal = (req) => {
    setCertModal(req);
    setCertContent("");
    setCertFileName("");
    setCertVerifyResult(null);
  };

  const handleCertFile = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setCertFileName(file.name);
    setCertVerifyResult(null);
    const reader = new FileReader();
    reader.onload = (ev) => setCertContent(ev.target.result);
    reader.readAsText(file);
  };

  const handleVerifyCert = async () => {
    if (!certContent || !certModal) return;
    setCertVerifyLoading(true);
    setCertVerifyResult(null);
    try {
      const result = await verifyCertSignature("arco_request", certModal.id, certContent);
      setCertVerifyResult(result);
    } catch (err) {
      setCertVerifyResult({ valid: false, message: extractApiError(err, "Error al verificar") });
    } finally {
      setCertVerifyLoading(false);
    }
  };

  // Firma necesaria para attend y review resolutivo (niveles 1-2)
  const needsSignature = level <= 2 && ["attend", "approve", "reject"].includes(actionType);

  const canonicalContent = actionReq
    ? buildCanonicalContent("arco_request", actionReq.id, {
        action: actionType,
        record_id: actionReq.record_id,
      })
    : "";

  const handleSubmitAction = async () => {
    if (needsSignature && !signatureData) {
      setError("Debes firmar la acción antes de continuar.");
      return;
    }
    setActionLoading(true);
    setError("");
    try {
      if (actionType === "attend") {
        await attendArcoRequest(actionReq.id, notes, signatureData?.contentHash, signatureData?.signatureB64);
        setSuccess(`Solicitud ${actionReq.folio || `#${actionReq.id}`} atendida y firmada.`);
      } else if (actionType === "escalate") {
        await escalateArcoRequest(actionReq.id, notes);
        setSuccess(`Solicitud ${actionReq.folio || `#${actionReq.id}`} escalada al administrador.`);
      } else if (actionType === "approve") {
        await reviewArcoRequest(actionReq.id, "approve", notes, signatureData?.contentHash, signatureData?.signatureB64);
        setSuccess(`Solicitud ${actionReq.folio || `#${actionReq.id}`} aprobada — registro anonimizado.`);
      } else if (actionType === "reject") {
        await reviewArcoRequest(actionReq.id, "reject", notes, signatureData?.contentHash, signatureData?.signatureB64);
        setSuccess(`Solicitud ${actionReq.folio || `#${actionReq.id}`} rechazada.`);
      }
      closeAction();
      await load();
    } catch (err) {
      setError(extractApiError(err, "Error al procesar la acción"));
    } finally {
      setActionLoading(false);
    }
  };

  const pageTitle = () => {
    if (level === 1) return "Solicitudes ARCO activas";
    if (level === 2) return "Solicitudes ARCO";
    return "Mis solicitudes ARCO";
  };

  const actionLabel = () => {
    if (actionType === "attend") return "Atender (cerrar)";
    if (actionType === "escalate") return "Escalar al administrador";
    if (actionType === "approve") return "Aprobar cancelación";
    if (actionType === "reject") return "Rechazar cancelación";
    return "";
  };

  const actionBtnClass = () => {
    if (actionType === "approve") return "button button-success";
    if (actionType === "reject" || actionType === "escalate") return "button button-danger";
    return "button button-primary";
  };

  const resolverName = certModal ? resolvedByName(certModal) : null;

  return (
    <main className="container">
      <AppNav />

      <div className="header">
        <h1 className="page-title">Módulo ARCO</h1>
        <p className="page-subtitle">{pageTitle()}</p>
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <p className="loading">Cargando...</p>
      ) : requests.length === 0 ? (
        <div className="card">
          <p style={{ color: "var(--text-muted)", textAlign: "center", padding: "2rem 0" }}>
            No hay solicitudes ARCO en este momento.
          </p>
        </div>
      ) : (
        <div className="card" style={{ overflowX: "auto" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Folio</th>
                <th>Tipo</th>
                <th>Estado</th>
                <th>Registro</th>
                {level !== 3 && <th>Solicitante</th>}
                <th>Razón</th>
                <th>Resuelta por</th>
                <th>Fecha</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((req) => {
                const resolver = resolvedByName(req);
                const isResolved = RESOLVED_STATUSES.includes(req.status);
                return (
                  <tr key={req.id}>
                    <td style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-muted)" }}>
                      {req.folio || `ARCO-${req.id}`}
                    </td>
                    <td>{TYPE_LABELS[req.request_type] || req.request_type}</td>
                    <td>
                      <span className={`badge ${STATUS_BADGE[req.status] || "badge-inactive"}`}>
                        {STATUS_LABELS[req.status] || req.status}
                      </span>
                    </td>
                    <td>{req.record_folio || `ID ${req.record_id}`}</td>
                    {level !== 3 && <td>{req.requested_by_name || req.requested_by_id}</td>}
                    <td style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {req.reason}
                    </td>
                    {/* Resuelta por */}
                    <td style={{ fontSize: 12 }}>
                      {isResolved && resolver ? (
                        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "nowrap" }}>
                          <span style={{ color: "var(--text-secondary)" }}>{resolver}</span>
                          <button
                            className="button button-ghost button-sm"
                            style={{ fontSize: 10, padding: "1px 6px", whiteSpace: "nowrap" }}
                            onClick={() => openCertModal(req)}
                          >
                            Verificar
                          </button>
                        </div>
                      ) : isResolved ? (
                        <span style={{ color: "var(--text-muted)", fontSize: 11 }}>Sin firma</span>
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>—</span>
                      )}
                    </td>
                    <td>{req.created_at ? new Date(req.created_at).toLocaleDateString("es-MX") : "—"}</td>
                    <td>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        {level === 2 && req.request_type !== "CANCELLATION" && ["PENDING", "IN_REVIEW"].includes(req.status) && (
                          <button className="button button-primary button-sm" onClick={() => openAction(req, "attend")}>Atender</button>
                        )}
                        {level === 2 && req.request_type === "CANCELLATION" && ["PENDING", "IN_REVIEW"].includes(req.status) && (
                          <button className="button button-warning button-sm" onClick={() => openAction(req, "escalate")}>Escalar</button>
                        )}
                        {level === 1 && req.request_type !== "CANCELLATION" && ["PENDING", "IN_REVIEW"].includes(req.status) && (
                          <button className="button button-primary button-sm" onClick={() => openAction(req, "attend")}>Atender</button>
                        )}
                        {level === 1 && req.request_type === "CANCELLATION" && req.status === "ESCALATED" && (
                          <>
                            <button className="button button-success button-sm" onClick={() => openAction(req, "approve")}>Aprobar</button>
                            <button className="button button-danger button-sm" onClick={() => openAction(req, "reject")}>Rechazar</button>
                          </>
                        )}
                        {level === 1 && req.request_type === "CANCELLATION" && ["PENDING", "IN_REVIEW"].includes(req.status) && (
                          <span style={{ color: "var(--text-muted)", fontSize: 11 }}>En revisión por coordinador</span>
                        )}
                        {!["PENDING", "IN_REVIEW", "ESCALATED"].includes(req.status) && level <= 2 && (
                          <span style={{ color: "var(--text-muted)", fontSize: 11 }}>—</span>
                        )}
                        {level === 3 && !isResolved && (
                          <span style={{ color: "var(--text-muted)", fontSize: 11 }}>—</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Modal de acción (attend / escalate / approve / reject) ── */}
      {actionReq && (
        <div className="modal-overlay" onClick={closeAction}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 500 }}>
            <h3 className="section-title">{actionLabel()}</h3>
            <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 12 }}>
              {actionReq.folio || `Solicitud #${actionReq.id}`} · {TYPE_LABELS[actionReq.request_type]} · {actionReq.record_folio || `Registro ${actionReq.record_id}`}
            </p>
            {actionType === "approve" && (
              <div className="alert alert-warning" style={{ marginBottom: 12, fontSize: 13 }}>
                Al aprobar esta cancelación los datos personales del registro serán anonimizados de forma permanente.
              </div>
            )}
            <div className="form-group">
              <label>Notas de resolución</label>
              <textarea className="input" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)}
                placeholder="Agrega notas sobre la resolución..." />
            </div>
            {needsSignature && (
              <SignaturePanel
                canonicalContent={canonicalContent}
                onSigned={(data) => setSignatureData(data)}
                signed={signatureData !== null}
              />
            )}
            {error && <div className="alert alert-error" style={{ marginBottom: 8, marginTop: 8 }}>{error}</div>}
            <div className="toolbar" style={{ marginTop: 12 }}>
              <button className="button button-ghost" onClick={closeAction} disabled={actionLoading}>Cancelar</button>
              <button className={actionBtnClass()} onClick={handleSubmitAction}
                disabled={actionLoading || (needsSignature && !signatureData)}>
                {actionLoading ? "Procesando..." : actionLabel()}
              </button>
            </div>
            {needsSignature && !signatureData && (
              <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6, textAlign: "right" }}>
                Firma requerida para continuar
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── Modal de verificación con .cer ── */}
      {certModal && (
        <div className="modal-overlay" onClick={() => setCertModal(null)}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 460 }}>
            <h3 className="section-title">Verificar firma</h3>
            <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 4 }}>
              {certModal.folio || `Solicitud #${certModal.id}`} · {TYPE_LABELS[certModal.request_type]}
            </p>
            {resolverName && (
              <p style={{ fontSize: 13, marginBottom: 14 }}>
                Resuelta por: <strong>{resolverName}</strong>
              </p>
            )}
            <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 14, lineHeight: 1.5 }}>
              Sube el certificado público <code>.cer</code> de <strong>{resolverName || "el firmante"}</strong> para
              comprobar que esta resolución fue firmada con su clave privada correspondiente.
            </p>
            <div className="form-group">
              <label style={{ fontSize: 13 }}>Certificado público del firmante (.cer)</label>
              <input
                type="file"
                accept=".cer,.pem"
                onChange={handleCertFile}
                className="input"
                style={{ fontSize: 12, padding: "6px 8px" }}
              />
              {certFileName && (
                <span style={{ fontSize: 11, color: "var(--accent)", marginTop: 3, display: "block" }}>
                  {certFileName}
                </span>
              )}
            </div>
            {certVerifyResult && (
              <div
                className={`alert ${certVerifyResult.valid ? "alert-success" : "alert-error"}`}
                style={{ fontSize: 13, marginBottom: 10 }}
              >
                {certVerifyResult.valid ? "✓ " : "✕ "}{certVerifyResult.message}
                {certVerifyResult.cert_cn && (
                  <div style={{ fontSize: 11, marginTop: 4, color: "inherit", opacity: 0.8 }}>
                    Certificado: {certVerifyResult.cert_cn}
                  </div>
                )}
              </div>
            )}
            <div className="toolbar" style={{ marginTop: 12 }}>
              <button className="button button-ghost" onClick={() => setCertModal(null)}>Cerrar</button>
              <button
                className="button button-primary"
                onClick={handleVerifyCert}
                disabled={certVerifyLoading || !certContent}
              >
                {certVerifyLoading ? "Verificando..." : "Verificar firma"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default ArcoPage;
