import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { ADMIN_ACCESS_LEVEL_CODE } from "../constants";

function AppNav() {
  const { user, logout } = useAuth();

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="header">
        <div>
          <strong>Identity Manager Demo</strong>
          <p style={{ margin: "4px 0 0" }}>
            {user?.full_name} · {user?.role_name}
          </p>
        </div>
        <div className="toolbar">
          <Link to="/" className="button secondary" style={{ textDecoration: "none", width: "auto" }}>
            Panel
          </Link>
          {user?.access_level_code === ADMIN_ACCESS_LEVEL_CODE ? (
            <Link
              to="/admin/users"
              className="button"
              style={{ textDecoration: "none", width: "auto" }}
            >
              Usuarios
            </Link>
          ) : null}
          <button type="button" className="button warning" onClick={logout} style={{ width: "auto" }}>
            Cerrar sesión
          </button>
        </div>
      </div>
    </div>
  );
}

export default AppNav;
