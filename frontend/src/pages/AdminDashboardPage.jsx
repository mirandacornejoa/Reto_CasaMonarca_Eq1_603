import AppNav from "../components/AppNav";
import { useAuth } from "../hooks/useAuth";

function AdminDashboardPage() {
  const { user } = useAuth();

  return (
    <main className="container">
      <AppNav />

      <div className="card">
        <h1 style={{ marginTop: 0 }}>Panel principal</h1>
        <p>
          Bienvenido, <strong>{user?.full_name}</strong>. Este sprint cubre login JWT, alta y activación de
          colaboradores, control de niveles y auditoría básica.
        </p>

        <div className="grid">
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Estado de sesión</h3>
            <p>Nivel: {user?.access_level_name}</p>
            <p>Rol: {user?.role_name}</p>
            <p>Área: {user?.area_name || "Sin área"}</p>
          </div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Permisos actuales</h3>
            <ul>
              {user?.permissions?.map((item) => (
                <li key={item.code}>{item.name}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </main>
  );
}

export default AdminDashboardPage;
