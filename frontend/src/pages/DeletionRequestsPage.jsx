import { useEffect, useState } from "react";
import AppNav from "../components/AppNav";
import SignaturePanel from "../components/SignaturePanel";
import { useAuth } from "../hooks/useAuth";
import { listDeletionRequests, reviewDeletionRequest } from "../api/deletionRequestsApi";
import { verifyCertSignature } from "../api/signaturesApi";
import { buildCanonicalContent } from "../utils/webCrypto";

function extractApiError(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => e.msg || String(e)).join(" · ");
  return fallback;
}

function DeletionRequestsPage() {
  const { user } = useAuth();
  const level = user?.access_level_code;
  const isAdmin = level === 1;

  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const [reviewModal, setReviewModal] = useState(null);
  const [notes, setNotes] = useState("");
  const [signatureData, setSignatureData] = useState(null);

  // Modal de verificación con .cer
  const [certModal, setCertModal] = useState(null);
  const [certContent, setCertContent] = useState("");
  const [certFileName, setCertFileName] = useState("");
  const [certVerifyLoading, setCertVerifyLoading] = useState(false);
  const [certVerifyResult, setCertVerifyResult] = useState(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await listDeletionRequests();
      setRequests(data);
    } catch (err) {
      setError(extractApiError(err, "Error cargando solicitudes"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const openReview = (id, action) => {
    setReviewModal({ id, action });
    setNotes("");
    setSignatureData(null);
    setError("");
  };

  const handleReview = async () => {
    if (!reviewModal) return;
    if (!signatureData) {
      setError("Debes firmar la acción antes de confirmar.");
      return;
    }
    setActionLoading(true);
    setError("");
    try {
      await reviewDeletionRequest(reviewModal.id, {
        action: reviewModal.action,
        notes: notes.trim() || null,
        content_hash: signatureData.contentHash,
        signature_b64: signatureData.signatureB64,
      });
      setSuccess(`Solicitud ${reviewModal.action === "approve" ? "aprobada" : "rechazada"} y firmada correctamente.`);
      setReviewModal(null);
      setNotes("");
      setSignatureData(null);
      await loadData();
    } catch (err) {
      setError(extractApiError(err, "Error al procesar solicitud"));
    } finally {
      setActionLoading(false);
    }
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
      const result = await verifyCertSignature("deletion_request", certModal.id, certContent);
      setCertVerifyResult(result);
    } catch (err) {
      setCertVerifyResult({ valid: false, message: extractApiError(err, "Error al verificar") });
    } finally {
      setCertVerifyLoading(false);
    }
  };

  // Contenido canónico de la firma para la solicitud en revisión
  const reviewReq = requests.find((r) => r.id === reviewModal?.id);
  const canonicalContent = reviewReq
    ? buildCanonicalContent("deletion_request", reviewReq.id, {
        action: reviewModal.action,
        record_id: reviewReq.record_id,
      })
    : "";

  const pending = requests.filter((r) => r.status === "pending");
  const resolved = requests.filter((r) => r.status !== "pending");

  const statusLabel = (s) => {
    if (s === "pending") return { text: "Pendiente", cls: "badge-pending" };
    if (s === "approved") return { text: "Aprobada", cls: "badge-active" };
    return { text: "Rechazada", cls: "badge-inactive" };
  };

  const fmtDate = (d) => d ? new Date(d).toLocaleString("es-MX", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

  return (
    <main className="container">
      <AppNav />

      <div className="header">
        <div>
          <h1 className="page-title">
            {isAdmin ? "Solicitudes de eliminación" : "Mis solicitudes de eliminación"}
          </h1>
          <p className="page-subtitle">
            {isAdmin
              ? "Revisa y decide sobre cada solicitud de los coordinadores."
              : "Estado de tus peticiones enviadas al administrador."}
          </p>
        </div>
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* ── Pendientes ── */}
      <div className="card deletion-card">
        <h3 className="section-title">
          {isAdmin ? `Pendientes de revisión (${pending.length})` : `Solicitudes enviadas (${requests.length})`}
        </h3>
        {loading ? (
          <p className="loading">Cargando...</p>
        ) : (isAdmin ? pending : requests).length === 0 ? (
          <div className="empty-state">
            <p>{isAdmin ? "No hay solicitudes pendientes." : "No has enviado solicitudes de eliminación."}</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Solicitud</th>
                  <th>Registro</th>
                  <th>Nombre</th>
                  {isAdmin && <th>Solicitado por</th>}
                  <th>Razón</th>
                  <th>Estado</th>
                  <th>Fecha</th>
                  {isAdmin && <th>Acciones</th>}
                </tr>
              </thead>
              <tbody>
                {(isAdmin ? pending : requests).map((r) => {
                  const sl = statusLabel(r.status);
                  return (
                    <tr key={r.id}>
                      <td style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-muted)" }}>{r.folio || `DEL-${r.id}`}</td>
                      <td style={{ fontWeight: 500 }}>{r.record_folio || `#${r.record_id}`}</td>
                      <td>{r.record_name || "—"}</td>
                      {isAdmin && <td>{r.requested_by_name || "—"}</td>}
                      <td style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", fontSize: 12, color: "var(--text-muted)" }}>
                        {r.reason}
                      </td>
                      <td>
                        <span className={`badge ${sl.cls}`}>{sl.text}</span>
                      </td>
                      <td style={{ fontSize: 12 }}>
                        {r.created_at ? new Date(r.created_at).toLocaleDateString("es-MX") : "—"}
                      </td>
                      {isAdmin && (
                        <td>
                          <div className="toolbar">
                            <button
                              className="button button-success button-sm"
                              onClick={() => openReview(r.id, "approve")}
                            >
                              Aprobar
                            </button>
                            <button
                              className="button button-danger button-sm"
                              onClick={() => openReview(r.id, "reject")}
                            >
                              Rechazar
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Historial resueltas ── */}
      {(isAdmin ? resolved.length > 0 : requests.filter((r) => r.status !== "pending").length > 0) && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3 className="section-title">Historial resuelto</h3>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Folio</th>
                  {isAdmin && <th>Solicitado por</th>}
                  <th>Estado</th>
                  <th>Resuelta por</th>
                  <th>Notas</th>
                  <th>Fecha resolución</th>
                </tr>
              </thead>
              <tbody>
                {(isAdmin ? resolved : requests.filter((r) => r.status !== "pending")).map((r) => {
                  const sl = statusLabel(r.status);
                  return (
                    <tr key={r.id}>
                      <td>{r.record_folio || `#${r.record_id}`}</td>
                      {isAdmin && <td>{r.requested_by_name || "—"}</td>}
                      <td><span className={`badge ${sl.cls}`}>{sl.text}</span></td>
                      <td style={{ fontSize: 12 }}>
                        {r.reviewed_by_name ? (
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <span>{r.reviewed_by_name}</span>
                            <button
                              className="button button-ghost button-sm"
                              style={{ fontSize: 10, padding: "1px 6px" }}
                              onClick={() => openCertModal(r)}
                            >
                              Verificar
                            </button>
                          </div>
                        ) : "—"}
                      </td>
                      <td style={{ maxWidth: 200, fontSize: 12, color: "var(--text-muted)" }}>
                        {r.review_notes || "—"}
                      </td>
                      <td style={{ fontSize: 12 }}>
                        {r.reviewed_at ? new Date(r.reviewed_at).toLocaleDateString("es-MX") : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Modal de revisión (admin) ── */}
      {reviewModal && (
        <div className="modal-overlay" onClick={() => { setReviewModal(null); setSignatureData(null); }}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 500 }}>
            <h3 className="section-title">
              {reviewModal.action === "approve" ? "Aprobar solicitud de eliminación" : "Rechazar solicitud de eliminación"}
            </h3>
            <div className="form-group">
              <label>Notas (opcional)</label>
              <textarea
                className="input"
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Agregar notas sobre la decisión..."
              />
            </div>

            {/* Firma digital requerida para admin */}
            <SignaturePanel
              canonicalContent={canonicalContent}
              onSigned={(data) => setSignatureData(data)}
              signed={signatureData !== null}
            />

            {error && <div className="alert alert-error" style={{ marginBottom: 8, marginTop: 8 }}>{error}</div>}
            <div className="toolbar" style={{ marginTop: 12 }}>
              <button className="button button-ghost" onClick={() => { setReviewModal(null); setSignatureData(null); }}>
                Cancelar
              </button>
              <button
                className={`button ${reviewModal.action === "approve" ? "button-success" : "button-danger"}`}
                disabled={actionLoading || !signatureData}
                onClick={handleReview}
              >
                {actionLoading
                  ? "Procesando..."
                  : reviewModal.action === "approve"
                  ? "Confirmar aprobación"
                  : "Confirmar rechazo"}
              </button>
            </div>
            {!signatureData && (
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
              {certModal.folio || `DEL-${certModal.id}`} — {certModal.record_name || `Registro #${certModal.record_id}`}
            </p>
            {certModal.reviewed_by_name && (
              <p style={{ fontSize: 13, marginBottom: 14 }}>
                Resuelta por: <strong>{certModal.reviewed_by_name}</strong>
              </p>
            )}
            <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 14, lineHeight: 1.5 }}>
              Sube el certificado público <code>.cer</code> de <strong>{certModal.reviewed_by_name || "el firmante"}</strong> para
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
                  <div style={{ fontSize: 11, marginTop: 4, opacity: 0.8 }}>
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

export default DeletionRequestsPage;
