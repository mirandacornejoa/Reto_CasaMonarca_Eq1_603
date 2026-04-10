import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { ADMIN_ACCESS_LEVEL_CODE } from "../constants";

function AdminRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <p className="container">Validando permisos...</p>;
  }

  if (!user || user.access_level_code !== ADMIN_ACCESS_LEVEL_CODE) {
    return <Navigate to="/" replace />;
  }

  return children;
}

export default AdminRoute;
