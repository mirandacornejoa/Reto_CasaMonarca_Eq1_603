import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppNav from "../components/AppNav";
import { useAuth } from "../hooks/useAuth";
import {
  listRecords,
  deleteRecord,
  reviewRecord,
} from "../api/recordsApi";
import { createDeletionRequest } from "../api/deletionRequestsApi";
import { getWorkflowBadgeClass, WORKFLOW_STATUSES } from "../constants";

function RecordsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const level = user?.access_level_code;

  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Filtros
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [actionLoading, setActionLoading] = useState(null);

  // Modal de eliminación
  const [deleteModal, setDeleteModal] = useState(null);
  const [deleteReason, setDeleteReason] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listRecords({
        workflow_status: filterStatus || undefined,
        search: search.trim() || undefined,
      });
      setRecords(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Error cargando registros");
    } finally {
      setLoading(false);
    }
  }, [filterStatus, search]);

  useEffect(() => {
    const timer = setTimeout(loadData, 300);
    return () => clearTimeout(timer);
  }, [loadData]);

  const clearMsg = () => { setError(""); setSuccess(""); };

  const doAction = async (recordId, action, label) => {
    clearMsg();
    setActionLoading(recordId);
    try {
      if (action === "review") await reviewRecord(recordId);
      else if (action === "delete") {
        await deleteRecord(recordId);
      }
      setSuccess(`Registro ${label}.`);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || `Error al ${label.toLowerCase()}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeletionRequest = async () => {
    if (!deleteModal || !deleteReason.trim()) {
      setError("La razón de eliminación es obligatoria.");
      return;
    }
    setActionLoading(deleteModal.id);
    try {
      await createDeletionRequest({
        record_id: deleteModal.id,
        reason: deleteReason.trim(),
      });
      setSuccess("Solicitud de eliminación enviada.");
      setDeleteModal(null);
      setDeleteReason("");
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al enviar solicitud");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <main className="container">
      <AppNav />

      <div className="header">
        <div>
          <h1 className="page-title">Registros de beneficiarios</h1>
          <p className="page-subtitle">
            {records.length} registro{records.length !== 1 ? "s" : ""} encontrado{records.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Link to="/records/new" className="button button-primary">
          + Nuevo registro
        </Link>
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* ── Filtros ── */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="form-row">
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{ fontSize: 12 }}>Buscar</label>
            <input
              className="input"
              placeholder="Folio, nombre, país..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{ fontSize: 12 }}>Estado workflow</label>
            <select
              className="select"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="">Todos</option>
              {WORKFLOW_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── Tabla ── */}
      <div className="card">
        {loading ? (
          <p className="loading">Cargando registros...</p>
        ) : records.length === 0 ? (
          <div className="empty-state">
            <p>No se encontraron registros.</p>
            <Link to="/records/new" className="button button-primary" style={{ marginTop: 12 }}>
              Crear primer registro
            </Link>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Folio</th>
                  <th>Nombre</th>
                  <th>País</th>
                  <th>Género</th>
                  <th>Workflow</th>
                  <th>Fecha</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => {
                  const name = r.first_name
                    ? `${r.first_name} ${r.last_name_1 || ""}`.trim()
                    : r.name_or_alias;
                  return (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 500, fontFamily: "monospace", fontSize: 12 }}>
                        {r.folio}
                      </td>
                      <td>{name}</td>
                      <td style={{ fontSize: 12 }}>{r.country_of_origin || r.nationality || "—"}</td>
                      <td style={{ fontSize: 12 }}>{r.gender || "—"}</td>
                      <td>
                        <span className={`badge ${getWorkflowBadgeClass(r.workflow_status)}`}>
                          {r.workflow_status || "—"}
                        </span>
                      </td>
                      <td style={{ fontSize: 12 }}>
                        {r.created_at ? new Date(r.created_at).toLocaleDateString("es-MX") : "—"}
                      </td>
                      <td>
                        <div className="toolbar" style={{ flexWrap: "wrap" }}>
                          <Link to={`/records/${r.id}`} className="button button-ghost button-sm">
                            Ver
                          </Link>

                          {/* Operativo: Aprobar (solo si no canalizado) y Canalizar */}
                          {level === 3 && !r.assigned_coordinator_id && r.workflow_status === "pendiente" && (
                            <button
                              className="button button-primary button-sm"
                              disabled={actionLoading === r.id}
                              onClick={() => doAction(r.id, "review", "aprobado")}
                            >
                              Aprobar
                            </button>
                          )}
                          {level === 3 && (
                            (r.workflow_status === "pendiente" && !r.assigned_coordinator_id) ||
                            r.workflow_status === "revisado"
                          ) && (
                            <button
                              className="button button-success button-sm"
                              disabled={actionLoading === r.id}
                              onClick={() => navigate(`/records/${r.id}`)}
                            >
                              {r.workflow_status === "revisado" ? "Re-canalizar" : "Canalizar"}
                            </button>
                          )}

                          {/* Coordinador: Aprobar y Petición de eliminación */}
                          {level === 2 && r.workflow_status === "pendiente" && (
                            <button
                              className="button button-primary button-sm"
                              disabled={actionLoading === r.id}
                              onClick={() => doAction(r.id, "review", "aprobado")}
                            >
                              Aprobar
                            </button>
                          )}
                          {level === 2 && (
                            <button
                              className="button button-danger button-sm"
                              onClick={() => setDeleteModal(r)}
                            >
                              Petición eliminar
                            </button>
                          )}

                          {/* Admin: Aprobar y Eliminar */}
                          {level === 1 && (
                            <>
                              {r.workflow_status === "pendiente" && (
                                <button
                                  className="button button-primary button-sm"
                                  disabled={actionLoading === r.id}
                                  onClick={() => doAction(r.id, "review", "aprobado")}
                                >
                                  Aprobar
                                </button>
                              )}
                              <button
                                className="button button-danger button-sm"
                                disabled={actionLoading === r.id}
                                onClick={() => {
                                  if (window.confirm(`¿Eliminar ${r.folio} definitivamente?`))
                                    doAction(r.id, "delete", "eliminado");
                                }}
                              >
                                Eliminar
                              </button>
                            </>
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
      </div>

      {/* ── Modal de solicitud de eliminación ── */}
      {deleteModal && (
        <div className="modal-overlay" onClick={() => setDeleteModal(null)}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 className="section-title">Petición de eliminación al administrador</h3>
            <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 12 }}>
              Registro: <strong>{deleteModal.folio}</strong> — {deleteModal.name_or_alias}
            </p>
            <div className="form-group">
              <label>Razón *</label>
              <textarea
                className="input"
                rows={3}
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                placeholder="Explica la razón..."
              />
            </div>
            <div className="toolbar">
              <button className="button button-ghost" onClick={() => setDeleteModal(null)}>
                Cancelar
              </button>
              <button
                className="button button-danger"
                disabled={actionLoading === deleteModal.id}
                onClick={handleDeletionRequest}
              >
                Enviar solicitud
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default RecordsPage;
