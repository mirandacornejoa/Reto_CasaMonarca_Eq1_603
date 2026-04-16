import { useEffect, useState } from "react";
import AppNav from "../components/AppNav";
import { useAuth } from "../hooks/useAuth";
import { ADMIN_ACCESS_LEVEL_CODE } from "../constants";
import { listUsers } from "../api/usersApi";
import { listRecords } from "../api/recordsApi";
import { listAuditLogs } from "../api/auditApi";

function DashboardPage() {
  const { user } = useAuth();
  const level = user?.access_level_code;
  const [stats, setStats] = useState({ users: 0, records: 0, auditEntries: 0 });

  useEffect(() => {
    const load = async () => {
      try {
        const promises = [];
        if (level === ADMIN_ACCESS_LEVEL_CODE) {
          promises.push(listUsers().then((d) => d.length).catch(() => 0));
        } else {
          promises.push(Promise.resolve(0));
        }
        if (level <= 3) {
          promises.push(listRecords({ limit: 1000 }).then((d) => d.length).catch(() => 0));
        } else {
          promises.push(Promise.resolve(0));
        }
        if (level === ADMIN_ACCESS_LEVEL_CODE) {
          promises.push(listAuditLogs(1).then((d) => d.length > 0 ? "✓" : "0").catch(() => "–"));
        } else {
          promises.push(Promise.resolve("–"));
        }
        const [uc, rc, ac] = await Promise.all(promises);
        setStats({ users: uc, records: rc, auditEntries: ac });
      } catch { /* ignore */ }
    };
    load();
  }, [level]);

  return (
    <main className="container">
      <AppNav />

      <h1 className="page-title">Panel principal</h1>
      <p className="page-subtitle">Bienvenido, {user?.full_name}. Tu sesión está activa.</p>

      <div className="grid" style={{ marginBottom: 20 }}>
        <div className="stat-card">
          <div className="stat-value">{user?.access_level_code}</div>
          <div className="stat-label">Nivel de acceso</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ fontSize: 16 }}>{user?.role_name}</div>
          <div className="stat-label">Rol asignado</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ fontSize: 16 }}>{user?.area_name || "Global"}</div>
          <div className="stat-label">Área</div>
        </div>
        {level <= 3 && (
          <div className="stat-card">
            <div className="stat-value">{stats.records}</div>
            <div className="stat-label">Registros</div>
          </div>
        )}
      </div>

      <div className="grid">
        <div className="card">
          <h3 className="section-title">Estado de la sesión</h3>
          <table>
            <tbody>
              <tr><td style={{ color: "var(--text-muted)" }}>Email</td><td>{user?.email}</td></tr>
              <tr><td style={{ color: "var(--text-muted)" }}>Estado</td><td><span className={`badge badge-${user?.status?.toLowerCase()}`}>{user?.status}</span></td></tr>
              <tr><td style={{ color: "var(--text-muted)" }}>Nivel</td><td>{user?.access_level_name}</td></tr>
              <tr><td style={{ color: "var(--text-muted)" }}>Rol</td><td>{user?.role_name}</td></tr>
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3 className="section-title">Permisos activos</h3>
          {user?.permissions?.length > 0 ? (
            <div className="chip-list">
              {user.permissions.map((p) => (
                <span key={p.code} className="chip selected">{p.name}</span>
              ))}
            </div>
          ) : (
            <p style={{ color: "var(--text-muted)", fontSize: 13 }}>Sin permisos asignados</p>
          )}
        </div>
      </div>
    </main>
  );
}

export default DashboardPage;
