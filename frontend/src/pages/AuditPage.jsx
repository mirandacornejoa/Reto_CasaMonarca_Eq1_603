import { useEffect, useState, useCallback } from "react";
import AppNav from "../components/AppNav";
import { listAuditLogs } from "../api/auditApi";

const ACTION_LABELS = {
  "records.create": "Crear registro",
  "records.update": "Editar registro",
  "records.delete": "Borrar registro",
  "records.review": "Aprobar registro",
  "records.channel": "Canalizar registro",
  "records.close": "Cerrar registro",
  "records.hash_query": "Consultar hash",
  "arco.create": "Crear solicitud ARCO",
  "arco.attend": "Resolver solicitud ARCO",
  "arco.escalate": "Escalar solicitud ARCO",
  "arco.approve_cancellation": "Aprobar cancelación ARCO",
  "arco.reject_cancellation": "Rechazar cancelación ARCO",
  "deletion_request.create": "Crear petición de eliminación",
  "deletion_request.approve": "Aprobar eliminación",
  "deletion_request.reject": "Rechazar eliminación",
  "identity.create_user": "Crear usuario",
  "identity.update_user": "Actualizar usuario",
  "identity.activate_user": "Activar usuario",
  "identity.deactivate_user": "Desactivar usuario",
  "certificates.issue": "Emitir certificado",
  "certificates.revoke": "Revocar certificado",
  "templates.create": "Crear plantilla",
  "templates.update": "Actualizar plantilla",
  "auth.login": "Iniciar sesión",
  "auth.logout": "Cerrar sesión",
};

function translateAction(action) {
  return ACTION_LABELS[action] || action;
}

function AuditPage() {
  const [logs, setLogs] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [filterAction, setFilterAction] = useState("");
  const [filterActor, setFilterActor] = useState("");
  const [filterMatricula, setFilterMatricula] = useState("");
  const [matriculaInput, setMatriculaInput] = useState("");
  const [expandedRows, setExpandedRows] = useState(new Set());

  const load = useCallback(async (matricula = "") => {
    setLoading(true);
    setError("");
    try {
      const data = await listAuditLogs(500, matricula);
      setLogs(data);
      setFiltered(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Error cargando bitácora");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(filterMatricula); }, [load, filterMatricula]);

  useEffect(() => {
    let result = logs;
    if (filterAction) {
      result = result.filter((l) =>
        translateAction(l.action).toLowerCase().includes(filterAction.toLowerCase())
      );
    }
    if (filterActor) {
      result = result.filter((l) =>
        (l.actor_name || "").toLowerCase().includes(filterActor.toLowerCase()) ||
        String(l.actor_user_id || "").includes(filterActor)
      );
    }
    setFiltered(result);
  }, [filterAction, filterActor, logs]);

  const applyMatricula = () => setFilterMatricula(matriculaInput.trim());
  const clearMatricula = () => { setMatriculaInput(""); setFilterMatricula(""); };

  const toggleRow = (id) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const fmtDate = (d) => new Date(d).toLocaleString("es-MX", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });

  const uniqueActions = [...new Set(logs.map((l) => l.action))].sort();

  return (
    <main className="container">
      <AppNav />

      <h1 className="page-title">Bitácora de auditoría</h1>
      <p className="page-subtitle">
        Registro inmutable de todas las operaciones. Haz clic en una fila para ver el detalle completo.
      </p>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Filtros */}
      <div className="card" style={{ marginBottom: 16, padding: 14 }}>
        <div className="form-row">
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Acción</label>
            <select className="select" value={filterAction} onChange={(e) => setFilterAction(e.target.value)}>
              <option value="">Todas las acciones</option>
              {uniqueActions.map((a) => (
                <option key={a} value={translateAction(a)}>{translateAction(a)}</option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Actor (nombre)</label>
            <input className="input" placeholder="Filtrar por nombre..."
              value={filterActor} onChange={(e) => setFilterActor(e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Matrícula</label>
            <div style={{ display: "flex", gap: 6 }}>
              <input className="input" placeholder="CM-USR-0001"
                value={matriculaInput} onChange={(e) => setMatriculaInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applyMatricula()}
                style={{ fontFamily: "monospace" }} />
              <button className="button button-primary button-sm" onClick={applyMatricula}>Buscar</button>
              {filterMatricula && (
                <button className="button button-ghost button-sm" onClick={clearMatricula}>✕</button>
              )}
            </div>
          </div>
        </div>
        {filterMatricula && (
          <p style={{ marginTop: 8, fontSize: 12, color: "var(--accent)" }}>
            Filtrando por matrícula: <strong>{filterMatricula}</strong> — {filtered.length} evento{filtered.length !== 1 ? "s" : ""}
          </p>
        )}
      </div>

      <div className="card">
        <h3 className="section-title">Eventos ({filtered.length})</h3>
        {loading ? <p className="loading">Cargando...</p> : filtered.length === 0 ? (
          <div className="empty-state"><p>No hay eventos que mostrar.</p></div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Folio evento</th>
                  <th>Fecha</th>
                  <th>Actor</th>
                  <th>Matrícula</th>
                  <th>Acción</th>
                  <th>Folio recurso</th>
                  <th>Resultado</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((log) => {
                  const isExpanded = expandedRows.has(log.id);
                  return (
                    <>
                      <tr
                        key={log.id}
                        style={{ cursor: log.detail ? "pointer" : "default" }}
                        onClick={() => log.detail && toggleRow(log.id)}
                      >
                        <td style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 600, color: "var(--accent)", whiteSpace: "nowrap" }}>
                          {log.folio || `BIT-${String(log.id).padStart(5, "0")}`}
                        </td>
                        <td style={{ fontSize: 11, whiteSpace: "nowrap", color: "var(--text-muted)" }}>
                          {fmtDate(log.created_at)}
                        </td>
                        <td style={{ fontSize: 12 }}>
                          {log.actor_name || (log.actor_user_id ? `ID:${log.actor_user_id}` : "Sistema")}
                          {log.actor_role && (
                            <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{log.actor_role}</div>
                          )}
                        </td>
                        <td style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-muted)" }}>
                          {log.actor_matricula || "—"}
                        </td>
                        <td>
                          <span style={{ fontSize: 12, color: "var(--accent)" }}>
                            {translateAction(log.action)}
                          </span>
                        </td>
                        <td style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-muted)" }}>
                          {log.resource_folio || "—"}
                        </td>
                        <td>
                          <span className={`badge ${log.result === "SUCCESS" ? "badge-active" : "badge-inactive"}`}>
                            {log.result === "SUCCESS" ? "Éxito" : "Error"}
                          </span>
                        </td>
                        <td style={{ fontSize: 11, maxWidth: 240 }}>
                          {log.detail ? (
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <span style={{
                                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                                maxWidth: 180, display: "inline-block",
                              }}>
                                {log.detail}
                              </span>
                              <span style={{ color: "var(--accent)", fontSize: 10, flexShrink: 0 }}>
                                {isExpanded ? "▲" : "▼"}
                              </span>
                            </div>
                          ) : "—"}
                        </td>
                      </tr>
                      {isExpanded && log.detail && (
                        <tr key={`${log.id}-detail`} style={{ background: "var(--bg-secondary)" }}>
                          <td colSpan={8} style={{ padding: "10px 16px", fontSize: 12, lineHeight: 1.7, color: "var(--text-secondary)", borderBottom: "1px solid var(--border)" }}>
                            <strong>Detalle completo:</strong><br />
                            <span style={{ whiteSpace: "pre-wrap" }}>{log.detail}</span>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}

export default AuditPage;
