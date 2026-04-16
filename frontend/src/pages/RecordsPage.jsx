import { useEffect, useState } from "react";
import AppNav from "../components/AppNav";
import { useAuth } from "../hooks/useAuth";
import { listRecords, createRecord, updateRecord } from "../api/recordsApi";
import { listAreas } from "../api/usersApi";
import { getStatusBadgeClass } from "../constants";

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

  const [form, setForm] = useState({
    name_or_alias: "", nationality: "", language: "", age_range: "",
    gender: "", contact_info: "", observations: "", status: "REGISTRADO",
    area_id: "",
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const params = {};
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      const [recs, areasData] = await Promise.all([listRecords(params), listAreas().catch(() => [])]);
      setRecords(recs);
      setAreas(areasData);
    } catch (err) {
      setError(err?.response?.data?.detail || "Error cargando registros");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [searchQuery, filterStatus]);

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

  const canEdit = user?.access_level_code <= 3;

  return (
    <main className="container">
      <AppNav />

      <div className="header">
        <div>
          <h1 className="page-title">Registros de migrantes</h1>
          <p className="page-subtitle">Gestión de expedientes con integridad SHA-256.</p>
        </div>
        {canEdit && (
          <button className="button button-primary" onClick={() => { setShowCreate(!showCreate); setEditingRecord(null); }}>
            {showCreate ? "Cancelar" : "+ Nuevo registro"}
          </button>
        )}
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Create / Edit Form */}
      {(showCreate || editingRecord) && canEdit && (
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
                  <th>Idioma</th>
                  <th>Edad</th>
                  <th>Estatus</th>
                  <th>Hash SHA-256</th>
                  {canEdit && <th>Acciones</th>}
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id}>
                    <td style={{ fontFamily: "monospace", fontSize: 12, color: "var(--accent)" }}>{r.folio || "–"}</td>
                    <td>{r.name_or_alias}</td>
                    <td>{r.nationality || "–"}</td>
                    <td style={{ fontSize: 12 }}>{r.language || "–"}</td>
                    <td style={{ fontSize: 12 }}>{r.age_range || "–"}</td>
                    <td><span className={`badge ${r.status === "CERRADO" ? "badge-inactive" : r.status === "ATENDIDO" ? "badge-active" : r.status === "EN_PROCESO" ? "badge-pending" : "badge-valid"}`}>{r.status}</span></td>
                    <td><span className="hash-display">{r.sha256_hash ? r.sha256_hash.slice(0, 16) + "..." : "–"}</span></td>
                    {canEdit && (
                      <td>
                        <button className="button button-ghost button-sm" onClick={() => startEdit(r)}>Editar</button>
                      </td>
                    )}
                  </tr>
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
