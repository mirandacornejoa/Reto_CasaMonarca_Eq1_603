import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { ADMIN_ACCESS_LEVEL_CODE, COORDINATOR_LEVEL_CODE, EXTERNAL_LEVEL_CODE } from "../constants";

const LEVEL_LABELS = { 1: "Admin", 2: "Coordinador", 3: "Operador", 4: "Voluntario" };

function AppNav() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const level = user?.access_level_code;

  const isActive = (path) =>
    location.pathname === path ? "nav-link active" : "nav-link";

  return (
    <nav className="nav-bar">
      <div className="nav-brand" style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
        <img src="/casa_monarca.png" alt="Casa Monarca" className="nav-logo" />
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <strong>{user?.full_name}</strong>
          <small>
            {LEVEL_LABELS[level] || "Usuario"} · {user?.area_name || "Sin área"}
          </small>
        </div>
      </div>
      <div className="nav-links">
        {/* Voluntarios (nivel 4) solo ven Nuevo Registro */}
        {level < EXTERNAL_LEVEL_CODE && (
          <Link to="/" className={isActive("/")}>
            Panel
          </Link>
        )}

        <Link to="/records/new" className={isActive("/records/new")}>
          Nuevo Registro
        </Link>

        {/* Ver registros: solo niveles 1-3 */}
        {level < EXTERNAL_LEVEL_CODE && (
          <Link to="/records" className={isActive("/records")}>
            Registros
          </Link>
        )}

        {/* Admin: usuarios, solicitudes, bitácora */}
        {level === ADMIN_ACCESS_LEVEL_CODE && (
          <>
            <Link to="/admin/users" className={isActive("/admin/users")}>
              Usuarios
            </Link>
            <Link to="/deletion-requests" className={isActive("/deletion-requests")}>
              Solicitudes
            </Link>
            <Link to="/audit" className={isActive("/audit")}>
              Bitácora
            </Link>
          </>
        )}

        {/* Coordinador: sus solicitudes de eliminación */}
        {level === COORDINATOR_LEVEL_CODE && (
          <Link to="/deletion-requests" className={isActive("/deletion-requests")}>
            Mis solicitudes
          </Link>
        )}

        {/* ARCO: niveles 1-3 */}
        {level < EXTERNAL_LEVEL_CODE && (
          <Link to="/arco" className={isActive("/arco")}>
            ARCO
          </Link>
        )}


        <Link to="/security/totp" className={isActive("/security/totp")}>
          2FA (TOTP)
        </Link>
        {/* Firma digital: solo admin y coordinador */}
        {level <= COORDINATOR_LEVEL_CODE && (
          <Link to="/security/signing" className={isActive("/security/signing")}>
            Firma digital
          </Link>
        )}

        <button
          type="button"
          className="nav-link"
          onClick={logout}
          style={{ color: "var(--danger)" }}
        >
          Cerrar sesión
        </button>
      </div>
    </nav>
  );
}

export default AppNav;
