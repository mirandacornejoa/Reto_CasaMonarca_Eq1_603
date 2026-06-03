import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppNav from "../components/AppNav";
import SignaturePanel from "../components/SignaturePanel";
import { useAuth } from "../hooks/useAuth";
import { getRecord, reviewRecord, channelRecord, deleteRecord, updateRecord, deleteRecordSigned } from "../api/recordsApi";
import { createDeletionRequest } from "../api/deletionRequestsApi";
import { createArcoRequest } from "../api/arcoApi";
import { getSignatureStatus, verifySignature } from "../api/signaturesApi";
import { buildCanonicalContent } from "../utils/webCrypto";
import { getWorkflowBadgeClass, GENDER_OPTIONS, CIVIL_STATUS_OPTIONS, AGE_RANGE_OPTIONS, POPULATION_GROUPS } from "../constants";

/** Normaliza un error de API: detail puede ser string o array de validación Pydantic. */
function extractApiError(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => e.msg || String(e)).join(" · ");
  return fallback;
}

function RecordDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const level = user?.access_level_code;

  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  // Modal canalizar
  const [showChannelModal, setShowChannelModal] = useState(false);
  const [channelNotes, setChannelNotes] = useState("");

  // Modal edición
  const [showEditModal, setShowEditModal] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [editLoading, setEditLoading] = useState(false);

  // Modal petición de eliminación (coordinador → admin)
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteReason, setDeleteReason] = useState("");

  // Modal eliminación directa con firma (solo admin)
  const [showAdminDeleteModal, setShowAdminDeleteModal] = useState(false);
  const [deleteSignature, setDeleteSignature] = useState(null);

  // Firma para edición
  const [editSignature, setEditSignature] = useState(null);

  // Modal ARCO
  const [showArcoModal, setShowArcoModal] = useState(false);
  const [arcoType, setArcoType] = useState("ACCESS");
  const [arcoReason, setArcoReason] = useState("");
  const [arcoDescription, setArcoDescription] = useState("");

  // Modal aprobar con firma (niveles 1-2)
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [approveSignature, setApproveSignature] = useState(null);

  // Estado de firma del registro
  const [signatureStatus, setSignatureStatus] = useState(null);
  const [sigVerifyResult, setSigVerifyResult] = useState(null);
  const [sigVerifyLoading, setSigVerifyLoading] = useState(false);

  const loadRecord = async () => {
    try {
      const data = await getRecord(id);
      setRecord(data);
      // Cargar estado de firma si el registro ya fue aprobado
      if (data.workflow_status === "revisado" || data.reviewed_at) {
        getSignatureStatus("record_approval", data.id)
          .then((sig) => setSignatureStatus(sig))
          .catch(() => setSignatureStatus({ signed: false }));
      }
    } catch (err) {
      setError(extractApiError(err, "Error cargando registro"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadRecord(); }, [id]);

  const handleApproveWithSignature = async () => {
    if (level <= 2 && !approveSignature) {
      setError("Debes firmar la acción antes de aprobar.");
      return;
    }
    setActionLoading(true);
    setError("");
    try {
      const payload = level <= 2
        ? { content_hash: approveSignature.contentHash, signature_b64: approveSignature.signatureB64 }
        : {};
      await reviewRecord(id, payload);
      setSuccess("Registro aprobado correctamente.");
      setShowApproveModal(false);
      setApproveSignature(null);
      await loadRecord();
    } catch (err) {
      setError(extractApiError(err, "Error al aprobar"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerifyRecordSig = async () => {
    setSigVerifyLoading(true);
    setSigVerifyResult(null);
    try {
      const data = await verifySignature("record_approval", record.id);
      setSigVerifyResult(data);
      setSignatureStatus((prev) => ({
        ...prev,
        last_verification_result: data.valid ? "VALID" : "INVALID",
      }));
    } catch (err) {
      setSigVerifyResult({ valid: false, message: extractApiError(err, "Error al verificar") });
    } finally {
      setSigVerifyLoading(false);
    }
  };

  const approveCanonical = record
    ? buildCanonicalContent("record_approval", record.id, { action: "approve" })
    : "";

  const handleAction = async (action, label) => {
    setActionLoading(true);
    setError(""); setSuccess("");
    try {
      if (action === "review") await reviewRecord(id);
      else if (action === "delete") {
        await deleteRecord(id);
        setSuccess("Registro eliminado.");
        setTimeout(() => navigate("/records"), 1500);
        return;
      }
      setSuccess(`Registro ${label} correctamente.`);
      await loadRecord();
    } catch (err) {
      setError(extractApiError(err, `Error al ${label.toLowerCase()}`));
    } finally {
      setActionLoading(false);
    }
  };

  const handleChannel = async () => {
    if (!channelNotes.trim()) {
      setError("El motivo de la canalización es obligatorio.");
      return;
    }
    setActionLoading(true);
    setError("");
    try {
      await channelRecord(id, channelNotes.trim());
      setSuccess("Registro canalizado al coordinador.");
      setShowChannelModal(false);
      setChannelNotes("");
      await loadRecord();
    } catch (err) {
      setError(extractApiError(err, "Error al canalizar"));
    } finally {
      setActionLoading(false);
    }
  };

  // Canónicos para firmas de edición y eliminación
  const editCanonical = record ? buildCanonicalContent("record_edit", record.id, { action: "edit" }) : "";
  const deleteCanonical = record ? buildCanonicalContent("record_delete", record.id, { action: "delete" }) : "";

  const openEditModal = () => {
    setEditSignature(null);
    setEditForm({
      first_name: record.first_name || "",
      last_name_1: record.last_name_1 || "",
      last_name_2: record.last_name_2 || "",
      phone: record.phone || "",
      gender: record.gender || "",
      country_of_origin: record.country_of_origin || "",
      state_department: record.state_department || "",
      civil_status: record.civil_status || "",
      age_range: record.age_range || "",
      population_group: record.population_group || "",
      nationality: record.nationality || "",
      observations: record.observations || "",
    });
    setShowEditModal(true);
    setError("");
  };

  const handleEdit = async () => {
    if (!editSignature) {
      setError("Debes firmar la edición antes de guardar.");
      return;
    }
    setEditLoading(true);
    setError("");
    try {
      const payload = {};
      Object.entries(editForm).forEach(([k, v]) => {
        if (v !== "") payload[k] = v || null;
      });
      await updateRecord(id, payload, editSignature);
      setSuccess("Registro actualizado correctamente.");
      setShowEditModal(false);
      await loadRecord();
    } catch (err) {
      setError(extractApiError(err, "Error al actualizar"));
    } finally {
      setEditLoading(false);
    }
  };

  const handleArcoRequest = async () => {
    if (!arcoReason.trim()) {
      setError("La razón de la solicitud ARCO es obligatoria.");
      return;
    }
    setActionLoading(true);
    try {
      await createArcoRequest({
        record_id: parseInt(id),
        request_type: arcoType,
        reason: arcoReason.trim(),
        description: arcoDescription.trim() || null,
      });
      setSuccess("Solicitud ARCO enviada correctamente.");
      setShowArcoModal(false);
      setArcoReason(""); setArcoDescription("");
    } catch (err) {
      setError(extractApiError(err, "Error al enviar solicitud ARCO"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeletionRequest = async () => {
    if (!deleteReason.trim()) {
      setError("La razón de eliminación es obligatoria.");
      return;
    }
    setActionLoading(true);
    try {
      await createDeletionRequest({ record_id: parseInt(id), reason: deleteReason.trim() });
      setSuccess("Solicitud de eliminación enviada al administrador.");
      setShowDeleteModal(false); setDeleteReason("");
    } catch (err) {
      setError(extractApiError(err, "Error al enviar solicitud"));
    } finally {
      setActionLoading(false);
    }
  };

  // Operativo puede aprobar solo si no ha sido canalizado al coordinador
  const canOperatorApprove = level === 3 && !record?.assigned_coordinator_id && record?.workflow_status === "pendiente";
  // Primera canalización: pendiente + sin coordinador asignado
  // Re-canalización: ya fue revisado/aprobado (coordinador terminó)
  const canOperatorChannel = level === 3 && (
    (record?.workflow_status === "pendiente" && !record?.assigned_coordinator_id) ||
    record?.workflow_status === "revisado"
  );

  if (loading) return (<main className="container"><AppNav /><p className="loading">Cargando registro...</p></main>);
  if (!record) return (<main className="container"><AppNav /><div className="alert alert-error">{error || "Registro no encontrado"}</div></main>);

  return (
    <main className="container">
      <AppNav />

      <div className="header">
        <div>
          <h1 className="page-title">Detalle del registro</h1>
          <p className="page-subtitle">{record.folio} · {record.name_or_alias}</p>
        </div>
        <div className="toolbar">
          <button className="button button-ghost" onClick={() => navigate("/records")}>
            ← Regresar
          </button>
        </div>
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {record.is_anonymized && (
        <div className="alert alert-info" style={{ marginBottom: 16 }}>
          Este registro ha sido anonimizado en cumplimiento de una solicitud ARCO de Cancelación aprobada.
        </div>
      )}

      {record.pending_deletion_folio && (
        <div className="alert alert-warning" style={{ marginBottom: 16, fontSize: 13 }}>
          Petición de eliminación pendiente · <strong>{record.pending_deletion_folio}</strong>
          {record.pending_deletion_by && <> · Solicitada por: <strong>{record.pending_deletion_by}</strong></>}
          {" "}→ En revisión por el Administrador
        </div>
      )}

      {/* ── Estado y acciones ── */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
          <span className={`badge ${getWorkflowBadgeClass(record.workflow_status)}`} style={{ fontSize: 13 }}>
            {record.workflow_status}
          </span>
          {record.assigned_coordinator_id && (
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
              Canalizado a: <strong>{record.assigned_coordinator_name || `#${record.assigned_coordinator_id}`}</strong>
              {record.channel_notes && <> · <em>{record.channel_notes}</em></>}
            </span>
          )}
        </div>

        <div className="actions-panel">
          <span className="actions-panel-label">Acciones</span>
          <div className="toolbar" style={{ flexWrap: "wrap" }}>
            {/* Editar: admin y coordinador */}
            {level <= 2 && !record.is_anonymized && (
              <button className="button button-primary button-sm" onClick={openEditModal}>
                Editar
              </button>
            )}

            {/* Aprobar: nivel 3 directo, niveles 1-2 con firma */}
            {canOperatorApprove && (
              <button className="button button-primary button-sm" disabled={actionLoading}
                onClick={() => handleAction("review", "aprobado")}>
                Aprobar
              </button>
            )}
            {level === 2 && record.workflow_status === "pendiente" && (
              <button className="button button-primary button-sm" disabled={actionLoading}
                onClick={() => { setApproveSignature(null); setShowApproveModal(true); }}>
                Aprobar
              </button>
            )}
            {level === 1 && record.workflow_status === "pendiente" && (
              <button className="button button-primary button-sm" disabled={actionLoading}
                onClick={() => { setApproveSignature(null); setShowApproveModal(true); }}>
                Aprobar
              </button>
            )}

            {/* Canalizar: operativo, solo si pendiente */}
            {canOperatorChannel && (
              <button className="button button-success button-sm" disabled={actionLoading}
                onClick={() => { setChannelNotes(""); setShowChannelModal(true); }}>
                {record.assigned_coordinator_id ? "Re-canalizar" : "Canalizar"}
              </button>
            )}

            {/* Solicitud ARCO: coordinador (2) y operativo (3) */}
            {(level === 2 || level === 3) && !record.is_anonymized && (
              <button className="button button-ghost button-sm"
                onClick={() => { setArcoType("ACCESS"); setArcoReason(""); setArcoDescription(""); setShowArcoModal(true); }}>
                Solicitud ARCO
              </button>
            )}

            {/* Petición de eliminación: coordinador */}
            {level === 2 && (
              <button className="button button-danger button-sm"
                onClick={() => setShowDeleteModal(true)}>
                Petición de eliminación
              </button>
            )}

            {/* Eliminar directo: solo admin — requiere firma */}
            {level === 1 && (
              <button className="button button-danger button-sm" disabled={actionLoading}
                onClick={() => { setDeleteSignature(null); setShowAdminDeleteModal(true); }}>
                Eliminar
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Datos ── */}
      <div className="card">
        <h3 className="section-title">Datos del beneficiario</h3>
        <div className="detail-grid">
          <DetailItem label="Folio" value={record.folio} />
          <DetailItem label="Fecha de atención" value={record.attention_date} />
          <DetailItem label="Nombre" value={record.first_name} />
          <DetailItem label="Primer apellido" value={record.last_name_1} />
          <DetailItem label="Segundo apellido" value={record.last_name_2} />
          <DetailItem label="Teléfono" value={record.phone} />
          <DetailItem label="Género" value={record.gender} />
          <DetailItem label="País de origen" value={record.country_of_origin} />
          <DetailItem label="Departamento / Estado" value={record.state_department} />
          <DetailItem label="Estado civil" value={record.civil_status} />
          <DetailItem label="Fecha de nacimiento" value={record.birth_date} />
          <DetailItem label="Edad" value={record.age_range} />
          <DetailItem label="Grupo de población" value={record.population_group} />
        </div>
      </div>

      {/* ── Información operativa ── */}
      <div className="card">
        <h3 className="section-title">Información operativa</h3>
        <div className="detail-grid">
          <DetailItem label="Estado workflow" value={
            <span className={`badge ${getWorkflowBadgeClass(record.workflow_status)}`}>
              {record.workflow_status}
            </span>
          } />
          <DetailItem label="Operador asignado" value={record.assigned_operator_name || "—"} />
          <DetailItem label="Coordinador asignado" value={record.assigned_coordinator_name || "—"} />
          <DetailItem label="Motivo de canalización" value={record.channel_notes || "—"} />
          <DetailItem label="Creado por" value={record.created_by_name || "—"} />
          <DetailItem label="Fecha de creación" value={record.created_at ? new Date(record.created_at).toLocaleString("es-MX") : "—"} />
          <DetailItem label="Aprobado" value={record.reviewed_at ? new Date(record.reviewed_at).toLocaleString("es-MX") : "—"} />
          <DetailItem label="Canalizado" value={record.channeled_at ? new Date(record.channeled_at).toLocaleString("es-MX") : "—"} />
        </div>
      </div>

      {/* ── Estado de firma de aprobación (visible para niveles 1-3) ── */}
      {(record.workflow_status === "revisado" || record.reviewed_at) && level <= 3 && (
        <div className="card">
          <h3 className="section-title">Resolución — Estado de firma</h3>
          {signatureStatus === null ? (
            <p style={{ color: "var(--text-muted)", fontSize: 13 }}>Cargando estado de firma...</p>
          ) : signatureStatus.signed ? (
            <div>
              <div className="alert alert-success" style={{ fontSize: 13, marginBottom: 10 }}>
                Esta aprobación fue firmada digitalmente.
              </div>
              <div className="detail-grid" style={{ marginBottom: 10 }}>
                <DetailItem label="Firmado por" value={
                  <span>{signatureStatus.signer_name}{signatureStatus.signer_matricula && <span style={{ color: "var(--text-muted)", fontSize: 11 }}> · {signatureStatus.signer_matricula}</span>}</span>
                } />
                <DetailItem label="Fecha de firma" value={signatureStatus.signed_at ? new Date(signatureStatus.signed_at).toLocaleString("es-MX") : "—"} />
                <DetailItem label="Algoritmo" value={<code style={{ fontSize: 11 }}>{signatureStatus.algorithm}</code>} />
                <DetailItem label="Huella digital" value={<code style={{ fontSize: 11 }}>{signatureStatus.fingerprint || "—"}</code>} />
                <DetailItem label="Última verificación" value={
                  signatureStatus.last_verification_result === "VALID"
                    ? <span style={{ color: "green" }}>Válida</span>
                    : signatureStatus.last_verification_result === "INVALID"
                    ? <span style={{ color: "red" }}>Inválida</span>
                    : "Sin verificar"
                } />
              </div>
              {sigVerifyResult && (
                <div className={`alert ${sigVerifyResult.valid ? "alert-success" : "alert-error"}`} style={{ fontSize: 12, marginBottom: 8 }}>
                  {sigVerifyResult.message}
                </div>
              )}
              <button className="button button-ghost button-sm" onClick={handleVerifyRecordSig} disabled={sigVerifyLoading}>
                {sigVerifyLoading ? "Verificando..." : "Verificar firma"}
              </button>
            </div>
          ) : (
            <div className="alert alert-warning" style={{ fontSize: 13 }}>
              Esta aprobación no tiene firma digital registrada (fue aprobada sin certificado).
            </div>
          )}
        </div>
      )}

      {record.observations && (
        <div className="card">
          <h3 className="section-title">Observaciones</h3>
          <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>{record.observations}</p>
        </div>
      )}

      {/* ── Modal Canalizar ── */}
      {showChannelModal && (
        <div className="modal-overlay" onClick={() => setShowChannelModal(false)}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 460 }}>
            <h3 className="section-title">Canalizar registro al coordinador</h3>
            <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 12 }}>
              Al canalizar, el registro pasará al coordinador asignado. Usted ya no podrá aprobarlo.
            </p>
            <div className="form-group">
              <label>Motivo de la canalización *</label>
              <textarea
                className="input"
                rows={3}
                value={channelNotes}
                onChange={(e) => setChannelNotes(e.target.value)}
                placeholder="Describe el motivo para canalizar este caso..."
              />
            </div>
            {error && <div className="alert alert-error" style={{ marginBottom: 8 }}>{error}</div>}
            <div className="toolbar">
              <button className="button button-ghost" onClick={() => setShowChannelModal(false)}>Cancelar</button>
              <button className="button button-primary" disabled={actionLoading} onClick={handleChannel}>
                {actionLoading ? "Canalizando..." : "Confirmar canalización"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal Editar ── */}
      {showEditModal && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 680 }}>
            <h3 className="section-title">Editar registro</h3>
            <div className="form-row">
              <div className="form-group">
                <label>Nombre</label>
                <input className="input" value={editForm.first_name || ""} onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Primer apellido</label>
                <input className="input" value={editForm.last_name_1 || ""} onChange={(e) => setEditForm({ ...editForm, last_name_1: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Segundo apellido</label>
                <input className="input" value={editForm.last_name_2 || ""} onChange={(e) => setEditForm({ ...editForm, last_name_2: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Teléfono</label>
                <input className="input" value={editForm.phone || ""} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Género</label>
                <select className="input" value={editForm.gender || ""} onChange={(e) => setEditForm({ ...editForm, gender: e.target.value })}>
                  <option value="">—</option>
                  {GENDER_OPTIONS.map((g) => <option key={g} value={g}>{g}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>País de origen</label>
                <input className="input" value={editForm.country_of_origin || ""} onChange={(e) => setEditForm({ ...editForm, country_of_origin: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Departamento / Estado</label>
                <input className="input" value={editForm.state_department || ""} onChange={(e) => setEditForm({ ...editForm, state_department: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Nacionalidad</label>
                <input className="input" value={editForm.nationality || ""} onChange={(e) => setEditForm({ ...editForm, nationality: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Estado civil</label>
                <select className="input" value={editForm.civil_status || ""} onChange={(e) => setEditForm({ ...editForm, civil_status: e.target.value })}>
                  <option value="">—</option>
                  {CIVIL_STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Grupo de población</label>
                <select className="input" value={editForm.population_group || ""} onChange={(e) => setEditForm({ ...editForm, population_group: e.target.value })}>
                  <option value="">—</option>
                  {POPULATION_GROUPS.map((g) => <option key={g} value={g}>{g}</option>)}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Observaciones</label>
              <textarea className="input" rows={3} value={editForm.observations || ""} onChange={(e) => setEditForm({ ...editForm, observations: e.target.value })} />
            </div>
            <SignaturePanel
              canonicalContent={editCanonical}
              onSigned={(data) => setEditSignature(data)}
              signed={editSignature !== null}
            />
            {error && <div className="alert alert-error" style={{ marginBottom: 8, marginTop: 8 }}>{error}</div>}
            <div className="toolbar" style={{ marginTop: 12 }}>
              <button className="button button-ghost" onClick={() => setShowEditModal(false)}>Cancelar</button>
              <button className="button button-primary" disabled={editLoading || !editSignature} onClick={handleEdit}>
                {editLoading ? "Guardando..." : "Guardar cambios"}
              </button>
            </div>
            {!editSignature && (
              <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6, textAlign: "right" }}>
                Firma requerida para guardar cambios
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── Modal ARCO ── */}
      {showArcoModal && (
        <div className="modal-overlay" onClick={() => { setShowArcoModal(false); setError(""); }}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
            <h3 className="section-title">Nueva solicitud ARCO</h3>
            <p style={{ color: "var(--text-muted)", marginBottom: 12, fontSize: 13 }}>
              Acceso · Rectificación · Cancelación · Oposición
            </p>
            <div className="form-group">
              <label>Tipo de solicitud *</label>
              <select className="input" value={arcoType} onChange={(e) => setArcoType(e.target.value)}>
                <option value="ACCESS">Acceso</option>
                <option value="RECTIFICATION">Rectificación</option>
                <option value="CANCELLATION">Cancelación</option>
                <option value="OPPOSITION">Oposición</option>
              </select>
            </div>
            <div className="form-group">
              <label>Razón *</label>
              <input className="input" value={arcoReason} onChange={(e) => { setArcoReason(e.target.value); setError(""); }}
                placeholder="Motivo de la solicitud ARCO..." />
            </div>
            <div className="form-group">
              <label>Descripción adicional</label>
              <textarea className="input" rows={3} value={arcoDescription}
                onChange={(e) => setArcoDescription(e.target.value)}
                placeholder="Detalles adicionales (opcional)..." />
            </div>
            {error && <div className="alert alert-error" style={{ marginBottom: 8 }}>{error}</div>}
            <div className="toolbar">
              <button className="button button-ghost" onClick={() => { setShowArcoModal(false); setError(""); }}>Cancelar</button>
              <button className="button button-primary" disabled={actionLoading} onClick={handleArcoRequest}>
                {actionLoading ? "Enviando..." : "Enviar solicitud ARCO"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal Eliminación directa con firma (admin) ── */}
      {showAdminDeleteModal && (
        <div className="modal-overlay" onClick={() => { setShowAdminDeleteModal(false); setDeleteSignature(null); }}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
            <h3 className="section-title">Eliminar registro</h3>
            <div className="alert alert-error" style={{ fontSize: 13, marginBottom: 14 }}>
              Esta acción eliminará permanentemente el registro <strong>{record?.folio}</strong> de la base de datos. Esta operación no se puede deshacer.
            </div>
            <SignaturePanel
              canonicalContent={deleteCanonical}
              onSigned={(data) => setDeleteSignature(data)}
              signed={deleteSignature !== null}
            />
            {error && <div className="alert alert-error" style={{ marginBottom: 8, marginTop: 8 }}>{error}</div>}
            <div className="toolbar" style={{ marginTop: 12 }}>
              <button className="button button-ghost" onClick={() => { setShowAdminDeleteModal(false); setDeleteSignature(null); }}>
                Cancelar
              </button>
              <button
                className="button button-danger"
                disabled={actionLoading || !deleteSignature}
                onClick={async () => {
                  if (!deleteSignature) return;
                  setActionLoading(true);
                  setError("");
                  try {
                    await deleteRecordSigned(id, deleteSignature);
                    setShowAdminDeleteModal(false);
                    setSuccess("Registro eliminado.");
                    setTimeout(() => navigate("/records"), 1500);
                  } catch (err) {
                    setError(extractApiError(err, "Error al eliminar"));
                  } finally {
                    setActionLoading(false);
                  }
                }}
              >
                {actionLoading ? "Eliminando..." : "Confirmar eliminación"}
              </button>
            </div>
            {!deleteSignature && (
              <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6, textAlign: "right" }}>
                Firma requerida para eliminar
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── Modal Aprobar con firma (niveles 1-2) ── */}
      {showApproveModal && (
        <div className="modal-overlay" onClick={() => { setShowApproveModal(false); setApproveSignature(null); }}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 500 }}>
            <h3 className="section-title">Aprobar registro</h3>
            <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 12 }}>
              Al aprobar, el registro cambiará de estado a <strong>revisado</strong>.
              Esta acción requiere tu firma digital.
            </p>
            <SignaturePanel
              canonicalContent={approveCanonical}
              onSigned={(data) => setApproveSignature(data)}
              signed={approveSignature !== null}
            />
            {error && <div className="alert alert-error" style={{ marginBottom: 8, marginTop: 8 }}>{error}</div>}
            <div className="toolbar" style={{ marginTop: 12 }}>
              <button className="button button-ghost" onClick={() => { setShowApproveModal(false); setApproveSignature(null); }}>
                Cancelar
              </button>
              <button
                className="button button-primary"
                disabled={actionLoading || !approveSignature}
                onClick={handleApproveWithSignature}
              >
                {actionLoading ? "Aprobando..." : "Confirmar aprobación"}
              </button>
            </div>
            {!approveSignature && (
              <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6, textAlign: "right" }}>
                Firma requerida para continuar
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── Modal Eliminación ── */}
      {showDeleteModal && (
        <div className="modal-overlay" onClick={() => { setShowDeleteModal(false); setError(""); }}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 className="section-title">Solicitar eliminación de registro</h3>
            <p style={{ color: "var(--text-muted)", marginBottom: 12, fontSize: 13 }}>
              Esta solicitud será enviada al administrador para su aprobación.
            </p>
            <div className="form-group">
              <label>Razón de la eliminación *</label>
              <textarea className="input" rows={3} value={deleteReason}
                onChange={(e) => { setDeleteReason(e.target.value); setError(""); }}
                placeholder="Explica la razón para eliminar este registro..." />
            </div>
            {error && <div className="alert alert-error" style={{ marginBottom: 8 }}>{error}</div>}
            <div className="toolbar">
              <button className="button button-ghost" onClick={() => { setShowDeleteModal(false); setError(""); }}>Cancelar</button>
              <button className="button button-danger" disabled={actionLoading} onClick={handleDeletionRequest}>
                {actionLoading ? "Enviando..." : "Enviar solicitud"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function DetailItem({ label, value }) {
  return (
    <div className="detail-item">
      <div className="detail-label">{label}</div>
      <div className="detail-value">{value || "—"}</div>
    </div>
  );
}

export default RecordDetailPage;
