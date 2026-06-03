import { useEffect, useState } from "react";
import AppNav from "../components/AppNav";
import { getStatusBadgeClass, USER_SUBTYPES, COORDINATOR_AREAS } from "../constants";
import {
  createCollaborator, listAreas, listLevels, listUsers,
  updateUserStatus, revokeUser, reactivateUser, updateUserExpiry,
  reissueCertificate, listOperators, listCoordinators, updateUserAssignment,
} from "../api/usersApi";

function UsersAdminPage() {
  const [users, setUsers] = useState([]);
  const [areas, setAreas] = useState([]);
  const [levels, setLevels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [expiryModal, setExpiryModal] = useState(null);
  const [expiryDate, setExpiryDate] = useState("");
  const [assignModal, setAssignModal] = useState(null); // { userId, currentLevel }
  const [assignTargetId, setAssignTargetId] = useState("");

  const [form, setForm] = useState({
    full_name: "", email: "", area_id: "", access_level_code: 3, expires_at: "",
    user_subtype: "", coordinator_area: "", assigned_to_id: "",
  });

  const [operators, setOperators] = useState([]);
  const [coordinators, setCoordinators] = useState([]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [u, a, l] = await Promise.all([listUsers(), listAreas(), listLevels()]);
      setUsers(u);
      setAreas(a);
      setLevels(l);
      if (!form.area_id && a.length) setForm((c) => ({ ...c, area_id: String(a[0].id) }));
      try {
        const [ops, coords] = await Promise.all([listOperators(), listCoordinators()]);
        setOperators(ops);
        setCoordinators(coords);
      } catch { /* operators/coordinators may not exist yet */ }
    } catch (err) {
      setError(err?.response?.data?.detail || "Error cargando datos");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const clearMessages = () => { setError(""); setSuccess(""); };

  const handleCreate = async (e) => {
    e.preventDefault();
    clearMessages();
    try {
      const payload = {
        full_name: form.full_name,
        email: form.email,
        area_id: form.area_id ? Number(form.area_id) : null,
        access_level_code: Number(form.access_level_code),
      };
      if (form.expires_at) payload.expires_at = new Date(form.expires_at).toISOString();
      if (Number(form.access_level_code) === 4 && form.user_subtype) payload.user_subtype = form.user_subtype;
      if (Number(form.access_level_code) === 2 && form.coordinator_area) payload.coordinator_area = form.coordinator_area;
      if (form.assigned_to_id) payload.assigned_to_id = Number(form.assigned_to_id);
      const result = await createCollaborator(payload);
      const linkMsg = result.activation_link
        ? ` Enlace de activación (demo): ${result.activation_link}`
        : " Enlace enviado por SMTP.";
      setSuccess(`Colaborador creado.${linkMsg}`);
      setForm((c) => ({ ...c, full_name: "", email: "", expires_at: "", user_subtype: "", coordinator_area: "", assigned_to_id: "" }));
      setShowCreate(false);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al crear colaborador");
    }
  };

  const handleAction = async (action, userId, label) => {
    clearMessages();
    if (action !== "reactivate" && !window.confirm(`¿${label} este usuario?`)) return;
    try {
      if (action === "deactivate") await updateUserStatus(userId, false);
      else if (action === "reactivate") await reactivateUser(userId);
      else if (action === "revoke") await revokeUser(userId);
      else if (action === "reissue") await reissueCertificate(userId);
      setSuccess(`Acción "${label}" completada.`);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || `Error: ${label}`);
    }
  };

  const handleAssignment = async () => {
    clearMessages();
    if (!assignModal) return;
    try {
      await updateUserAssignment(assignModal.userId, assignTargetId ? Number(assignTargetId) : null);
      setSuccess("Asignación actualizada.");
      setAssignModal(null);
      setAssignTargetId("");
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al actualizar asignación");
    }
  };

  const handleExpiry = async () => {
    clearMessages();
    if (!expiryDate || !expiryModal) return;
    try {
      await updateUserExpiry(expiryModal, { expires_at: new Date(expiryDate).toISOString() });
      setSuccess("Vigencia actualizada.");
      setExpiryModal(null);
      setExpiryDate("");
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al actualizar vigencia");
    }
  };

  const fmtDate = (d) => d ? new Date(d).toLocaleDateString("es-MX", { year: "numeric", month: "short", day: "numeric" }) : "–";

  return (
    <main className="container">
      <AppNav />

      <div className="header">
        <div>
          <h1 className="page-title">Gestión de usuarios</h1>
          <p className="page-subtitle">Administra colaboradores, roles, vigencia y certificados internos.</p>
        </div>
        <button className="button button-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "Cancelar" : "+ Nuevo colaborador"}
        </button>
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {showCreate && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 className="section-title">Alta de colaborador</h3>
          <form onSubmit={handleCreate}>
            <div className="form-row">
              <div className="form-group">
                <label>Nombre completo</label>
                <input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Correo electrónico</label>
                <input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Área</label>
                <select className="select" value={form.area_id} onChange={(e) => setForm({ ...form, area_id: e.target.value })}>
                  <option value="">-- Sin área --</option>
                  {areas.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Nivel de acceso</label>
                <select className="select" value={form.access_level_code} onChange={(e) => setForm({ ...form, access_level_code: e.target.value, user_subtype: "", coordinator_area: "", assigned_to_id: "" })} required>
                  {levels.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Vigencia hasta (opcional)</label>
                <input className="input" type="date" value={form.expires_at} onChange={(e) => setForm({ ...form, expires_at: e.target.value })} />
              </div>
            </div>

            {/* Campos jerárquicos dinámicos */}
            <div className="form-row">
              {Number(form.access_level_code) === 4 && (
                <>
                  <div className="form-group">
                    <label>Subtipo de usuario</label>
                    <select className="select" value={form.user_subtype} onChange={(e) => setForm({ ...form, user_subtype: e.target.value })}>
                      <option value="">-- Seleccionar --</option>
                      {USER_SUBTYPES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Asignar a operativo</label>
                    <select className="select" value={form.assigned_to_id} onChange={(e) => setForm({ ...form, assigned_to_id: e.target.value })}>
                      <option value="">-- Seleccionar --</option>
                      {operators.map((o) => <option key={o.id} value={o.id}>{o.full_name}</option>)}
                    </select>
                  </div>
                </>
              )}
              {Number(form.access_level_code) === 3 && (
                <div className="form-group">
                  <label>Asignar a coordinador</label>
                  <select className="select" value={form.assigned_to_id} onChange={(e) => setForm({ ...form, assigned_to_id: e.target.value })}>
                    <option value="">-- Seleccionar --</option>
                    {coordinators.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}
                  </select>
                </div>
              )}
              {Number(form.access_level_code) === 2 && (
                <div className="form-group">
                  <label>Área de coordinación</label>
                  <select className="select" value={form.coordinator_area} onChange={(e) => setForm({ ...form, coordinator_area: e.target.value })}>
                    <option value="">-- Seleccionar --</option>
                    {COORDINATOR_AREAS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
                  </select>
                </div>
              )}
            </div>

            <button className="button button-primary" type="submit">Crear colaborador</button>
          </form>
        </div>
      )}

      {/* Assignment Modal */}
      {assignModal && (
        <div className="modal-overlay" onClick={() => setAssignModal(null)}>
          <div className="modal-content card" onClick={(e) => e.stopPropagation()}>
            <h3 className="section-title">Cambiar asignación jerárquica</h3>
            <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 12 }}>
              {assignModal.currentLevel === 4
                ? "Asignar este voluntario a un operativo"
                : "Asignar este operativo a un coordinador"}
            </p>
            <div className="form-group">
              <label>
                {assignModal.currentLevel === 4 ? "Operativo" : "Coordinador"}
              </label>
              <select
                className="select"
                value={assignTargetId}
                onChange={(e) => setAssignTargetId(e.target.value)}
              >
                <option value="">-- Sin asignación --</option>
                {(assignModal.currentLevel === 4 ? operators : coordinators).map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
            </div>
            <div className="toolbar">
              <button className="button button-primary" onClick={handleAssignment}>
                Guardar
              </button>
              <button className="button button-ghost" onClick={() => setAssignModal(null)}>
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Expiry Modal */}
      {expiryModal && (
        <div className="modal-overlay" onClick={() => setExpiryModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 className="section-title">Renovar vigencia</h3>
            <div className="form-group">
              <label>Nueva fecha de expiración</label>
              <input className="input" type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} required />
            </div>
            <div className="toolbar">
              <button className="button button-primary" onClick={handleExpiry} disabled={!expiryDate}>Guardar</button>
              <button className="button button-secondary" onClick={() => setExpiryModal(null)}>Cancelar</button>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h3 className="section-title">Usuarios registrados</h3>
        {loading ? <p className="loading">Cargando...</p> : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Matrícula</th>
                  <th>Nombre</th>
                  <th>Email</th>
                  <th>Área</th>
                  <th>Nivel</th>
                  <th>Subtipo</th>
                  <th>Asignado a</th>
                  <th>Estado</th>
                  <th>Vigencia</th>
                  <th>Certificado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-muted)" }}>{u.matricula || "—"}</td>
                    <td>{u.full_name}</td>
                    <td style={{ fontSize: 12, color: "var(--text-muted)" }}>{u.email}</td>
                    <td>{u.area_name || "–"}</td>
                    <td style={{ fontSize: 12 }}>{u.access_level_name}</td>
                    <td style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      {u.user_subtype || u.coordinator_area || "–"}
                    </td>
                    <td style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      {u.assigned_to_name || "–"}
                    </td>
                    <td><span className={`badge ${getStatusBadgeClass(u.status)}`}>{u.status}</span></td>
                    <td style={{ fontSize: 12 }}>{fmtDate(u.expires_at)}</td>
                    <td>
                      {u.certificate_status ? (
                        <span className={`badge ${getStatusBadgeClass(u.certificate_status)}`}>{u.certificate_status}</span>
                      ) : "–"}
                    </td>
                    <td>
                      <div className="toolbar">
                        {u.status === "ACTIVE" && (
                          <button className="button button-warning button-sm" onClick={() => handleAction("deactivate", u.id, "Desactivar")}>Desactivar</button>
                        )}
                        {(u.status === "INACTIVE" || u.status === "REVOKED") && (
                          <button className="button button-success button-sm" onClick={() => handleAction("reactivate", u.id, "Reactivar")}>Reactivar</button>
                        )}
                        {u.status === "ACTIVE" && (
                          <button className="button button-danger button-sm" onClick={() => handleAction("revoke", u.id, "Revocar")}>Revocar</button>
                        )}
                        {(u.access_level_code === 3 || u.access_level_code === 4) && (
                          <button
                            className="button button-ghost button-sm"
                            onClick={() => {
                              setAssignTargetId(u.assigned_to_id ? String(u.assigned_to_id) : "");
                              setAssignModal({ userId: u.id, currentLevel: u.access_level_code });
                            }}
                          >
                            Asignación
                          </button>
                        )}
                        <button className="button button-ghost button-sm" onClick={() => { setExpiryModal(u.id); setExpiryDate(""); }}>Vigencia</button>
                        {u.certificate_id && (
                          <button className="button button-ghost button-sm" onClick={() => handleAction("reissue", u.id, "Re-emitir certificado")}>Re-emitir cert</button>
                        )}
                      </div>
                    </td>
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

export default UsersAdminPage;
