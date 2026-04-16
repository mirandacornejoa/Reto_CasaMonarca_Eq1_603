import { useEffect, useState } from "react";
import AppNav from "../components/AppNav";
import { listAuditLogs } from "../api/auditApi";

function AuditPage() {
  const [logs, setLogs] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const [filterActor, setFilterActor] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const data = await listAuditLogs(500);
        setLogs(data);
        setFiltered(data);
      } catch (err) {
        setError(err?.response?.data?.detail || "Error cargando bitácora");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  useEffect(() => {
    let result = logs;
    if (filterAction) {
      result = result.filter((l) => l.action.toLowerCase().includes(filterAction.toLowerCase()));
    }
    if (filterActor) {
      result = result.filter((l) =>
        (l.actor_name || "").toLowerCase().includes(filterActor.toLowerCase()) ||
        String(l.actor_user_id).includes(filterActor)
      );
    }
    setFiltered(result);
  }, [filterAction, filterActor, logs]);

  const fmtDate = (d) => new Date(d).toLocaleString("es-MX", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });

  const uniqueActions = [...new Set(logs.map((l) => l.action))].sort();

  return (
    <main className="container">
      <AppNav />

      <h1 className="page-title">Bitácora de auditoría</h1>
      <p className="page-subtitle">Registro inmutable de todas las operaciones del sistema.</p>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Filters */}
      <div className="card" style={{ marginBottom: 16, padding: 14 }}>
        <div className="form-row">
          <div className="form-group" style={{ marginBottom: 0 }}>
            <select className="select" value={filterAction} onChange={(e) => setFilterAction(e.target.value)}>
              <option value="">Todas las acciones</option>
              {uniqueActions.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <input className="input" placeholder="Filtrar por actor..." value={filterActor} onChange={(e) => setFilterActor(e.target.value)} />
          </div>
        </div>
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
                  <th>Fecha</th>
                  <th>Actor</th>
                  <th>Rol</th>
                  <th>Acción</th>
                  <th>Recurso</th>
                  <th>Resultado</th>
                  <th>Detalle</th>
                  <th>Hash</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((log) => (
                  <tr key={log.id}>
                    <td style={{ fontSize: 11, whiteSpace: "nowrap", color: "var(--text-muted)" }}>{fmtDate(log.created_at)}</td>
                    <td style={{ fontSize: 12 }}>{log.actor_name || (log.actor_user_id ? `ID:${log.actor_user_id}` : "Sistema")}</td>
                    <td style={{ fontSize: 11, color: "var(--text-muted)" }}>{log.actor_role || "–"}</td>
                    <td>
                      <span style={{ fontSize: 11, fontFamily: "monospace", color: "var(--accent)" }}>{log.action}</span>
                    </td>
                    <td style={{ fontSize: 12 }}>
                      {log.resource}
                      {log.resource_id && <span style={{ color: "var(--text-muted)" }}> #{log.resource_id}</span>}
                    </td>
                    <td>
                      <span className={`badge ${log.result === "SUCCESS" ? "badge-active" : "badge-inactive"}`}>
                        {log.result}
                      </span>
                    </td>
                    <td style={{ fontSize: 11, maxWidth: 250, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {log.detail || "–"}
                    </td>
                    <td>
                      {log.hash_related ? (
                        <span className="hash-display">{log.hash_related.slice(0, 12)}...</span>
                      ) : "–"}
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

export default AuditPage;
