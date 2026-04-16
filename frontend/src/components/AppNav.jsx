import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { ADMIN_ACCESS_LEVEL_CODE, EXTERNAL_LEVEL_CODE } from "../constants";

function AppNav() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const level = user?.access_level_code;

  const isActive = (path) => location.pathname === path ? "nav-link active" : "nav-link";

  return (
    <nav className="nav-bar">
      <div className="nav-brand">
        <strong>Casa Monarca — Gestor de Identidades</strong>
        <small>{user?.full_name} · {user?.role_name} · {user?.area_name || "Sin área"}</small>
      </div>
      <div className="nav-links">
        <Link to="/" className={isActive("/")}>Panel</Link>

        {level <= 3 && (
          <Link to="/records" className={isActive("/records")}>Registros</Link>
        )}

        {level === ADMIN_ACCESS_LEVEL_CODE && (
          <>
            <Link to="/admin/users" className={isActive("/admin/users")}>Usuarios</Link>
            <Link to="/audit" className={isActive("/audit")}>Bitácora</Link>
            <Link to="/templates" className={isActive("/templates")}>Plantillas</Link>
          </>
        )}

        <button type="button" className="nav-link" onClick={logout} style={{ color: "var(--danger)" }}>
          Cerrar sesión
        </button>
      </div>
    </nav>
  );
}

export default AppNav;
