import { useEffect, useState, useCallback } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import AppNav from "../components/AppNav";
import { useAuth } from "../hooks/useAuth";
import { getDashboardStats } from "../api/dashboardApi";
import { reviewRecord } from "../api/recordsApi";
import { createDeletionRequest } from "../api/deletionRequestsApi";
import { getWorkflowBadgeClass } from "../constants";

function DashboardPage() {
  const { user } = useAuth();
  const level = user?.access_level_code;

  // Nivel 4: redirigir al formulario
  if (level >= 4) {
    return <Navigate to="/records/new" replace />;
  }

  return <DashboardContent user={user} level={level} />;
}

function DashboardContent({ user, level }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [actionLoading, setActionLoading] = useState(null);

  // Modal petición de eliminar
  const [deleteModal, setDeleteModal] = useState(null);
  const [deleteReason, setDeleteReason] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const d = await getDashboardStats();
      setData(d);
    } catch (err) {
      setError(err?.response?.data?.detail || "Error cargando panel");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const doAction = async (recordId, action) => {
    // Canalizar y aprobar con firma siempre van al detalle del registro
    if (action === "channel" || action === "review_signed") {
      navigate(`/records/${recordId}`);
      return;
    }
    setActionLoading(recordId + action);
    setError("");
    setSuccess("");
    try {
      if (action === "review") {
        // Solo nivel 3 puede aprobar sin firma desde el panel
        await reviewRecord(recordId);
        setSuccess("Registro aprobado.");
      }
      await load();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(
        typeof detail === "string" ? detail
          : Array.isArray(detail) ? detail.map((e) => e.msg || String(e)).join(" · ")
          : "Error al procesar acción"
      );
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeletionRequest = async () => {
    if (!deleteModal || !deleteReason.trim()) {
      setError("La razón de eliminación es obligatoria.");
      return;
    }
    setActionLoading("del-" + deleteModal.id);
    try {
      await createDeletionRequest({ record_id: deleteModal.id, reason: deleteReason.trim() });
      setSuccess("Petición de eliminación enviada al administrador.");
      setDeleteModal(null);
      setDeleteReason("");
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al enviar petición");
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <main className="container">
        <AppNav />
        <p className="loading">Cargando panel...</p>
      </main>
    );
  }

  return (
    <main className="container">
      <AppNav />

      <div className="header">
        <div>
          <h1 className="page-title">
            {level === 1 && "Panel de Administración"}
            {level === 2 && "Panel de Coordinación"}
            {level === 3 && "Panel Operativo"}
          </h1>
          <p className="page-subtitle">
            Bienvenido, {user?.full_name} · {user?.role_name}
            {data?.area_name ? ` · ${data.area_name}` : ""}
          </p>
        </div>
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* ── Acciones rápidas ── */}
      <div className="quick-actions">
        <Link to="/records/new" className="action-card">
          <span className="action-icon">📝</span>
          <span className="action-text">Nuevo registro</span>
        </Link>
        {level <= 3 && (
          <Link to="/records" className="action-card">
            <span className="action-icon">📋</span>
            <span className="action-text">Ver registros</span>
          </Link>
        )}
        {level === 1 && (
          <>
            <Link to="/admin/users" className="action-card">
              <span className="action-icon">👥</span>
              <span className="action-text">Gestionar usuarios</span>
            </Link>
            <Link to="/deletion-requests" className="action-card">
              <span className="action-icon">🗑</span>
              <span className="action-text">Solicitudes de eliminación</span>
            </Link>
            <Link to="/audit" className="action-card">
              <span className="action-icon">📜</span>
              <span className="action-text">Bitácora</span>
            </Link>
          </>
        )}
        {level === 2 && (
          <Link to="/deletion-requests" className="action-card">
            <span className="action-icon">📋</span>
            <span className="action-text">Mis solicitudes</span>
          </Link>
        )}
      </div>

      {/* ── Admin: resumen global + solicitudes pendientes ── */}
      {level === 1 && data && (
        <>
          <div className="dashboard-section">
            <div className="stats-grid">
              <StatCard label="Total registros" value={data.total_records || 0} />
              <StatCard label="Pendientes" value={data.pending_records || 0} color="#f59e0b" />
              <StatCard label="Revisados" value={data.reviewed_records || 0} color="#3b82f6" />
            </div>
          </div>

          {data.pending_deletions?.length > 0 && (
            <div className="card deletion-card dashboard-section">
              <h3 className="section-title">
                Solicitudes de eliminación pendientes ({data.pending_deletions.length})
              </h3>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Folio</th>
                      <th>Nombre</th>
                      <th>Solicitado por</th>
                      <th>Razón</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.pending_deletions.map((d, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 500 }}>{d.record_folio || `#${d.record_id}`}</td>
                        <td>{d.record_name || "—"}</td>
                        <td>{d.requested_by_name || "—"}</td>
                        <td style={{ fontSize: 12, color: "var(--text-muted)", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>
                          {d.reason}
                        </td>
                        <td>
                          <Link to="/deletion-requests" className="button button-ghost button-sm">
                            Revisar →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {data.pending_deletions?.length === 0 && (
            <div className="card dashboard-section">
              <p style={{ color: "var(--text-muted)", textAlign: "center", padding: "24px 0" }}>
                No hay solicitudes de eliminación pendientes.
              </p>
            </div>
          )}

          {/* ARCO activas */}
          {data.pending_arco?.length > 0 && (
            <div className="card dashboard-section">
              <h3 className="section-title">
                Solicitudes ARCO activas ({data.pending_arco.length})
              </h3>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Folio</th>
                      <th>Tipo</th>
                      <th>Estado</th>
                      <th>Solicitante</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.pending_arco.map((ar) => (
                      <tr key={ar.id}>
                        <td style={{ fontWeight: 500 }}>{ar.record_folio || `#${ar.record_id}`}</td>
                        <td style={{ fontSize: 12 }}>{ar.request_type}</td>
                        <td style={{ fontSize: 12 }}>{ar.status}</td>
                        <td>{ar.requested_by_name || "—"}</td>
                        <td>
                          <Link to="/arco" className="button button-ghost button-sm">
                            Revisar →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {data.pending_arco?.length === 0 && (
            <div className="card dashboard-section">
              <p style={{ color: "var(--text-muted)", textAlign: "center", padding: "24px 0" }}>
                No hay solicitudes ARCO activas.
              </p>
            </div>
          )}
        </>
      )}

      {/* ── Operativo (3): bandeja de registros de sus voluntarios ── */}
      {level === 3 && data && (
        <WorkTray
          title="Registros pendientes de mis voluntarios"
          emptyMsg="No hay registros pendientes de tus voluntarios asignados."
          items={data.work_items || []}
          actionLoading={actionLoading}
          actions={(item) => (
            <>
              {item.workflow_status === "pendiente" && (
                <button
                  className="button button-primary button-sm"
                  disabled={actionLoading === item.id + "review"}
                  onClick={() => doAction(item.id, "review")}
                >
                  Aprobar
                </button>
              )}
              {!item.assigned_coordinator_id && (
                <button
                  className="button button-success button-sm"
                  disabled={actionLoading === item.id + "channel"}
                  onClick={() => doAction(item.id, "channel")}
                >
                  Canalizar
                </button>
              )}
            </>
          )}
        />
      )}

      {/* ── Coordinador (2): registros canalizados a él ── */}
      {level === 2 && data && (
        <WorkTray
          title="Registros canalizados a mí"
          emptyMsg="No hay registros canalizados pendientes."
          items={data.work_items || []}
          actionLoading={actionLoading}
          actions={(item) => (
            <>
              {item.workflow_status === "pendiente" && (
                <button
                  className="button button-primary button-sm"
                  onClick={() => doAction(item.id, "review_signed")}
                  title="Requiere firma digital — abre el detalle del registro"
                >
                  Aprobar
                </button>
              )}
              <button
                className="button button-ghost button-sm"
                onClick={() => navigate(`/records/${item.id}`)}
              >
                Ver detalle
              </button>
              <button
                className="button button-danger button-sm"
                onClick={() => setDeleteModal(item)}
              >
                Petición eliminar
              </button>
            </>
          )}
        />
      )}

      {/* ── Notificaciones de resoluciones — niveles 2-3 (siempre al final) ── */}
      {(level === 2 || level === 3) && data?.notifications?.length > 0 && (
        <div className="card dashboard-section" style={{ borderLeft: "3px solid var(--accent)" }}>
          <h3 className="section-title">Notificaciones de resoluciones ({data.notifications.length})</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {data.notifications.map((n) => {
              const badgeClass = ["APPROVED", "approved"].includes(n.status)
                ? "badge-active"
                : ["COMPLETED"].includes(n.status)
                ? "badge-valid"
                : "badge-revoked";
              const destPath = n.kind === "deletion" ? "/deletion-requests" : "/arco";
              return (
                <div key={`${n.kind}-${n.id}`} style={{
                  padding: "10px 14px",
                  background: "var(--bg-secondary)",
                  borderRadius: 6,
                  fontSize: 13,
                  display: "flex",
                  flexDirection: "column",
                  gap: 4,
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <span style={{ fontFamily: "monospace", fontSize: 11, color: "var(--accent)", fontWeight: 600 }}>
                      {n.folio}
                    </span>
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{n.type_label}</span>
                    <span className={`badge ${badgeClass}`} style={{ fontSize: 10 }}>
                      {n.status_label}
                    </span>
                    {n.record_folio && (
                      <span style={{ color: "var(--text-muted)", fontSize: 11 }}>· Registro: {n.record_folio}</span>
                    )}
                  </div>
                  <div style={{ color: "var(--text-secondary)" }}>
                    {n.resolver_name
                      ? <><strong>{n.resolver_name}</strong> resolvió tu {n.type_label.toLowerCase()}</>
                      : <>Tu {n.type_label.toLowerCase()} fue resuelta</>
                    }
                  </div>
                  {n.resolution_notes && (
                    <div style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>
                      Nota: {n.resolution_notes}
                    </div>
                  )}
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 4 }}>
                    <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      {n.resolved_at ? new Date(n.resolved_at).toLocaleString("es-MX", {
                        day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
                      }) : "—"}
                    </span>
                    <button
                      className="button button-ghost button-sm"
                      style={{ fontSize: 11 }}
                      onClick={() => navigate(destPath)}
                    >
                      Ver →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Modal petición de eliminación ── */}
      {deleteModal && (
        <div className="modal-overlay" onClick={() => setDeleteModal(null)}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 className="section-title">Petición de eliminación al administrador</h3>
            <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 12 }}>
              Registro: <strong>{deleteModal.folio}</strong> — {deleteModal.name}
            </p>
            <div className="form-group">
              <label>Razón *</label>
              <textarea
                className="input"
                rows={3}
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                placeholder="Explica la razón para solicitar la eliminación..."
              />
            </div>
            <div className="toolbar">
              <button className="button button-ghost" onClick={() => setDeleteModal(null)}>
                Cancelar
              </button>
              <button
                className="button button-danger"
                disabled={actionLoading === "del-" + deleteModal?.id}
                onClick={handleDeletionRequest}
              >
                Enviar petición
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function WorkTray({ title, emptyMsg, items, actionLoading, actions }) {
  return (
    <div className="card dashboard-section">
      <h3 className="section-title">{title} ({items.length})</h3>
      {items.length === 0 ? (
        <div className="empty-state">
          <p>{emptyMsg}</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Folio</th>
                <th>Nombre</th>
                <th>País</th>
                <th>Estado</th>
                <th>Fecha</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const name = item.first_name
                  ? `${item.first_name} ${item.last_name_1 || ""}`.trim()
                  : item.name;
                return (
                  <tr key={item.id}>
                    <td style={{ fontWeight: 500, fontFamily: "monospace", fontSize: 12 }}>
                      {item.folio}
                    </td>
                    <td>{name}</td>
                    <td style={{ fontSize: 12 }}>{item.country_of_origin || "—"}</td>
                    <td>
                      <span className={`badge ${getWorkflowBadgeClass(item.workflow_status)}`}>
                        {item.workflow_status}
                      </span>
                    </td>
                    <td style={{ fontSize: 12 }}>
                      {item.created_at ? new Date(item.created_at).toLocaleDateString("es-MX") : "—"}
                    </td>
                    <td>
                      <div className="toolbar" style={{ flexWrap: "wrap" }}>
                        {actions(item)}
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
  );
}

function StatCard({ label, value, color }) {
  return (
    <div className="stat-card">
      <div className="stat-value" style={color ? { color } : {}}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export default DashboardPage;
