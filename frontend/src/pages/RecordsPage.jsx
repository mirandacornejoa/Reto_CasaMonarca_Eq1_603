import React, { useEffect, useState, useRef } from "react";
import AppNav from "../components/AppNav";
import { useAuth } from "../hooks/useAuth";
import { listRecords, createRecord, updateRecord, deleteRecord, getResourceSignatures } from "../api/recordsApi";
import { listAreas } from "../api/usersApi";
import { signingStatus, signingVerify } from "../api/authApi";
import { signContent, buildCanonicalContent } from "../utils/webCrypto";
import { ADMIN_ACCESS_LEVEL_CODE } from "../constants";

const RECORD_STATUSES = ["REGISTRADO", "EN_PROCESO", "ATENDIDO", "CERRADO"];

function RecordsPage() {
  const { user } = useAuth();
  const [records, setRecords] = useState([]);
  const [areas, setAreas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  // Signing state — per user
  const [signingReady, setSigningReady] = useState(false);
  const [signatureMap, setSignatureMap] = useState({});
  const [viewingSigs, setViewingSigs] = useState(null);

  // Sign modal: archivo .key + contraseña
  const [showSignModal, setShowSignModal] = useState(false);
  const [signModalRecord, setSignModalRecord] = useState(null);
  const [signKeyContent, setSignKeyContent] = useState("");
  const [signKeyFileName, setSignKeyFileName] = useState("");
  const [signPassword, setSignPassword] = useState("");
  const [signError, setSignError] = useState("");
  const [signing, setSigning] = useState(false);
  const fileInputRef = useRef(null);

  const [form, setForm] = useState({
    name_or_alias: "", nationality: "", language: "", age_range: "",
    gender: "", contact_info: "", observations: "", status: "REGISTRADO",
    area_id: "",
  });

  // RBAC: admin=CRUD, coordinator=CRU, operator=CR, external=C
  const level = user?.access_level_code;
  const canCreate = true; // Todos los niveles pueden crear
  const canEdit = level <= 2; // Solo admin y coordinador
  const canDelete = level === ADMIN_ACCESS_LEVEL_CODE; // Solo admin

  // Reset signing state when user changes (fixes cross-user contamination bug)
  useEffect(() => {
    setSigningReady(false);
    setSignatureMap({});
    setViewingSigs(null);
    setShowSignModal(false);
    setSignKeyContent("");
    setSignKeyFileName("");
    setSignPassword("");
    setSignError("");
  }, [user?.id]);

  const loadData = async () => {
    setLoading(true);
    try {
      const params = {};
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      const [recs, areasData] = await Promise.all([listRecords(params), listAreas().catch(() => [])]);
      setRecords(recs);
      setAreas(areasData);

      // Verificar estado de certificado del usuario actual en backend
      try {
        const status = await signingStatus();
        setSigningReady(status?.has_signing_cert && status?.status === "VALID");
      } catch {
        setSigningReady(false);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || "Error cargando registros");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [searchQuery, filterStatus, user?.id]);

  const clearMsg = () => { setError(""); setSuccess(""); };

  const handleCreate = async (e) => {
    e.preventDefault();
    clearMsg();
    try {
      const payload = { ...form };
      if (payload.area_id) payload.area_id = Number(payload.area_id);
      else delete payload.area_id;
      Object.keys(payload).forEach((k) => { if (!payload[k]) delete payload[k]; });
      await createRecord(payload);
      setSuccess("Registro creado correctamente.");
      setShowCreate(false);
      setForm({ name_or_alias: "", nationality: "", language: "", age_range: "", gender: "", contact_info: "", observations: "", status: "REGISTRADO", area_id: "" });
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al crear registro");
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    clearMsg();
    if (!editingRecord) return;
    try {
      const payload = {};
      if (form.name_or_alias) payload.name_or_alias = form.name_or_alias;
      if (form.nationality) payload.nationality = form.nationality;
      if (form.language) payload.language = form.language;
      if (form.age_range) payload.age_range = form.age_range;
      if (form.gender) payload.gender = form.gender;
      if (form.contact_info) payload.contact_info = form.contact_info;
      if (form.observations !== undefined) payload.observations = form.observations;
      if (form.status) payload.status = form.status;
      if (form.area_id) payload.area_id = Number(form.area_id);
      await updateRecord(editingRecord.id, payload);
      setSuccess("Registro actualizado. Hash SHA-256 recalculado.");
      setEditingRecord(null);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al actualizar");
    }
  };

  const handleDelete = async (record) => {
    if (!window.confirm(`¿Eliminar permanentemente el registro ${record.folio} — ${record.name_or_alias}? Esta acción no se puede deshacer.`)) return;
    clearMsg();
    try {
      await deleteRecord(record.id);
      setSuccess(`Registro ${record.folio} eliminado correctamente.`);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al eliminar registro");
    }
  };

  const startEdit = (rec) => {
    setEditingRecord(rec);
    setShowCreate(false);
    setForm({
      name_or_alias: rec.name_or_alias || "",
      nationality: rec.nationality || "",
      language: rec.language || "",
      age_range: rec.age_range || "",
      gender: rec.gender || "",
      contact_info: rec.contact_info || "",
      observations: rec.observations || "",
      status: rec.status || "REGISTRADO",
      area_id: rec.area_id ? String(rec.area_id) : "",
    });
  };

  // ── Signing ──

  const handleRequestSign = (record) => {
    clearMsg();
    setSignModalRecord(record);
    setSignKeyContent("");
    setSignKeyFileName("");
    setSignPassword("");
    setSignError("");
    setShowSignModal(true);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setSignKeyFileName(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => setSignKeyContent(ev.target.result);
    reader.readAsText(file);
  };

  const handleConfirmSign = async () => {
    if (!signKeyContent) {
      setSignError("Selecciona tu archivo de clave privada (.key).");
      return;
    }
    if (!signPassword) {
      setSignError("Ingresa la contraseña de tu clave privada.");
      return;
    }
    setSigning(true);
    setSignError("");
    try {
      const record = signModalRecord;
      const canonical = buildCanonicalContent("migrant_record", record.id, {
        folio: record.folio,
        name_or_alias: record.name_or_alias,
        sha256_hash: record.sha256_hash,
        status: record.status,
      });

      // Descifrar archivo .key + firmar en memoria
      const { contentHash, signatureB64 } = await signContent(canonical, signKeyContent, signPassword);

      // Enviar firma al backend para verificación y registro
      const result = await signingVerify("migrant_record", record.id, contentHash, signatureB64);
      setShowSignModal(false);
      setSignKeyContent("");
      setSignPassword("");

      if (result.is_valid) {
        setSuccess(`Registro ${record.folio} firmado y verificado correctamente.`);
        loadSignaturesForRecord(record.id);
      } else {
        setError(`La firma fue rechazada: ${result.message}`);
      }
    } catch (err) {
      const msg = err?.message || err?.response?.data?.detail || "Error al firmar";
      // Distinguir errores específicos para mejor UX
      if (msg.includes("Contraseña incorrecta")) {
        setSignError("❌ Contraseña incorrecta. Verifica la contraseña de tu clave privada.");
      } else if (msg.includes("formato") || msg.includes("corrupto")) {
        setSignError("❌ Archivo inválido. Asegúrate de seleccionar tu archivo .key correcto.");
      } else if (msg.includes("no corresponde") || msg.includes("no tiene certificado")) {
        setShowSignModal(false);
        setSignKeyContent("");
        setSignPassword("");
        setError("❌ El archivo no corresponde a tu cuenta o no tienes certificado activo.");
      } else if (msg.includes("revocado")) {
        setShowSignModal(false);
        setError("❌ Tu certificado de firma ha sido revocado. Genera uno nuevo en Configurar Firma.");
      } else if (msg.includes("expirado")) {
        setShowSignModal(false);
        setError("❌ Tu certificado de firma ha expirado. Genera uno nuevo en Configurar Firma.");
      } else {
        setSignError(msg);
      }
    } finally {
      setSigning(false);
    }
  };

  const loadSignaturesForRecord = async (recordId) => {
    try {
      const sigs = await getResourceSignatures("migrant_record", recordId);
      setSignatureMap((prev) => ({ ...prev, [recordId]: sigs }));
    } catch { /* silent */ }
  };

  const handleViewSignatures = async (recordId) => {
    if (viewingSigs === recordId) {
      setViewingSigs(null);
      return;
    }
    await loadSignaturesForRecord(recordId);
    setViewingSigs(recordId);
  };

  return (
    <main className="container">
      <AppNav />

      <div className="header">
        <div>
          <h1 className="page-title">Registros de migrantes</h1>
          <p className="page-subtitle">Gestión de expedientes con integridad SHA-256 y firma digital.</p>
        </div>
        {canCreate && (
          <button className="button button-primary" onClick={() => { setShowCreate(!showCreate); setEditingRecord(null); }}>
            {showCreate ? "Cancelar" : "+ Nuevo registro"}
          </button>
        )}
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Sign modal: archivo .key + contraseña */}
      {showSignModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center",
          justifyContent: "center", zIndex: 1000,
        }}>
          <div className="card" style={{ maxWidth: 440, width: "90%", margin: 20 }}>
            <h3 style={{ marginBottom: 8 }}>✍ Firmar registro {signModalRecord?.folio}</h3>
            <p style={{ fontSize: "0.85em", color: "var(--text-muted)", marginBottom: 12 }}>
              Para firmar, selecciona tu archivo de clave privada (.key) e ingresa la contraseña
              que definiste al generar tu certificado de firma.
            </p>

            {signError && <div className="alert alert-error" style={{ marginBottom: 12, fontSize: "0.85em" }}>{signError}</div>}

            <div className="form-group">
              <label>Archivo de clave privada (.key)</label>
              <input
                type="file"
                accept=".key,.pem,.txt"
                onChange={handleFileSelect}
                ref={fileInputRef}
                style={{ fontSize: "0.9em" }}
              />
              {signKeyFileName && (
                <p style={{ fontSize: "0.75em", color: "var(--accent)", marginTop: 4, marginBottom: 0 }}>
                  🔑 {signKeyFileName}
                </p>
              )}
            </div>

            <div className="form-group">
              <label>Contraseña de la clave privada</label>
              <input
                type="password"
                className="input"
                placeholder="Contraseña de tu clave de firma"
                value={signPassword}
                onChange={(e) => setSignPassword(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleConfirmSign(); }}
              />
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="button button-primary"
                style={{ flex: 1 }}
                onClick={handleConfirmSign}
                disabled={signing || !signKeyContent || !signPassword}
              >
                {signing ? "Firmando..." : "✍ Firmar registro"}
              </button>
              <button
                className="button"
                onClick={() => { setShowSignModal(false); setSignKeyContent(""); setSignPassword(""); setSignError(""); }}
                disabled={signing}
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create / Edit Form */}
      {(showCreate || editingRecord) && (canCreate || canEdit) && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 className="section-title">{editingRecord ? `Editar: ${editingRecord.folio}` : "Nuevo registro"}</h3>
          <form onSubmit={editingRecord ? handleUpdate : handleCreate}>
            <div className="form-row">
              <div className="form-group">
                <label>Nombre o alias *</label>
                <input className="input" value={form.name_or_alias} onChange={(e) => setForm({ ...form, name_or_alias: e.target.value })} required={!editingRecord} />
              </div>
              <div className="form-group">
                <label>Nacionalidad</label>
                <input className="input" value={form.nationality} onChange={(e) => setForm({ ...form, nationality: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Idioma</label>
                <input className="input" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Rango de edad</label>
                <select className="select" value={form.age_range} onChange={(e) => setForm({ ...form, age_range: e.target.value })}>
                  <option value="">– Sin especificar –</option>
                  <option>Menor de 18</option>
                  <option>18-24</option>
                  <option>25-34</option>
                  <option>35-44</option>
                  <option>45-54</option>
                  <option>55-64</option>
                  <option>65+</option>
                  <option>(grupo familiar)</option>
                </select>
              </div>
              <div className="form-group">
                <label>Género</label>
                <input className="input" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Medio de contacto</label>
                <input className="input" value={form.contact_info} onChange={(e) => setForm({ ...form, contact_info: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Estatus</label>
                <select className="select" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                  {RECORD_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              {areas.length > 0 && (
                <div className="form-group">
                  <label>Área</label>
                  <select className="select" value={form.area_id} onChange={(e) => setForm({ ...form, area_id: e.target.value })}>
                    <option value="">– Sin área –</option>
                    {areas.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </select>
                </div>
              )}
            </div>
            <div className="form-group">
              <label>Observaciones</label>
              <textarea className="input textarea" value={form.observations} onChange={(e) => setForm({ ...form, observations: e.target.value })} />
            </div>
            <div className="toolbar">
              <button className="button button-primary" type="submit">{editingRecord ? "Guardar cambios" : "Crear registro"}</button>
              {editingRecord && <button className="button button-secondary" type="button" onClick={() => setEditingRecord(null)}>Cancelar</button>}
            </div>
          </form>
        </div>
      )}

      {/* Filters */}
      <div className="card" style={{ marginBottom: 16, padding: 14 }}>
        <div className="form-row">
          <div className="form-group" style={{ marginBottom: 0 }}>
            <input className="input" placeholder="Buscar por nombre, folio o nacionalidad..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <select className="select" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">Todos los estatus</option>
              {RECORD_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Records Table */}
      <div className="card">
        <h3 className="section-title">Expedientes ({records.length})</h3>
        {loading ? <p className="loading">Cargando...</p> : records.length === 0 ? (
          <div className="empty-state"><p>No se encontraron registros.</p></div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Folio</th>
                  <th>Nombre/Alias</th>
                  <th>Nacionalidad</th>
                  <th>Estatus</th>
                  <th>Hash SHA-256</th>
                  <th>Firma</th>
                  {(canEdit || canDelete) && <th>Acciones</th>}
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <React.Fragment key={r.id}>
                    <tr>
                      <td style={{ fontFamily: "monospace", fontSize: 12, color: "var(--accent)" }}>{r.folio || "–"}</td>
                      <td>{r.name_or_alias}</td>
                      <td>{r.nationality || "–"}</td>
                      <td><span className={`badge ${r.status === "CERRADO" ? "badge-inactive" : r.status === "ATENDIDO" ? "badge-active" : r.status === "EN_PROCESO" ? "badge-pending" : "badge-valid"}`}>{r.status}</span></td>
                      <td><span className="hash-display">{r.sha256_hash ? r.sha256_hash.slice(0, 12) + "..." : "–"}</span></td>
                      <td>
                        {signingReady ? (
                          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                            <button
                              className="button button-ghost button-sm"
                              onClick={() => handleRequestSign(r)}
                              title="Firmar este registro"
                              style={{ fontSize: 11, padding: "2px 6px" }}
                            >
                              ✍ Firmar
                            </button>
                            <button
                              className="button button-ghost button-sm"
                              onClick={() => handleViewSignatures(r.id)}
                              title="Ver firmas"
                              style={{ fontSize: 11, padding: "2px 6px" }}
                            >
                              {signatureMap[r.id]?.length ? `📋 ${signatureMap[r.id].length}` : "📋"}
                            </button>
                          </div>
                        ) : (
                          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>–</span>
                        )}
                      </td>
                      {(canEdit || canDelete) && (
                        <td>
                          <div style={{ display: "flex", gap: 4 }}>
                            {canEdit && (
                              <button className="button button-ghost button-sm" onClick={() => startEdit(r)}>Editar</button>
                            )}
                            {canDelete && (
                              <button
                                className="button button-ghost button-sm"
                                style={{ color: "var(--danger, red)" }}
                                onClick={() => handleDelete(r)}
                              >
                                Eliminar
                              </button>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                    {viewingSigs === r.id && signatureMap[r.id] && (
                      <tr>
                        <td colSpan={(canEdit || canDelete) ? 7 : 6} style={{ padding: "8px 12px", background: "var(--bg-elevated, rgba(255,255,255,0.03))" }}>
                          {signatureMap[r.id].length === 0 ? (
                            <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0 }}>Sin firmas registradas</p>
                          ) : (
                            <div>
                              <p style={{ fontSize: 11, color: "var(--text-muted)", margin: "0 0 6px 0", fontWeight: 600 }}>
                                Firmas ({signatureMap[r.id].length}):
                              </p>
                              {signatureMap[r.id].map((sig) => (
                                <div key={sig.id} style={{
                                  fontSize: 11, display: "flex", gap: 12, alignItems: "center",
                                  padding: "3px 0", borderBottom: "1px solid var(--border, #333)",
                                }}>
                                  <span style={{ color: sig.last_verification_result === "VALID" ? "var(--success, green)" : "var(--danger, red)" }}>
                                    {sig.last_verification_result === "VALID" ? "✓" : "✗"} {sig.last_verification_result}
                                  </span>
                                  <span>{sig.signer_name || `User #${sig.signer_user_id}`}</span>
                                  <span style={{ color: "var(--text-muted)" }}>{sig.algorithm}</span>
                                  <span style={{ color: "var(--text-muted)" }}>
                                    {sig.signed_at ? new Date(sig.signed_at).toLocaleString() : "–"}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}

export default RecordsPage;
