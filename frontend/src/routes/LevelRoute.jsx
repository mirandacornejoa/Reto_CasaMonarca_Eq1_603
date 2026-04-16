import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

function LevelRoute({ maxLevel, children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <p className="loading">Validando permisos...</p>;
  }

  if (!user || (user.access_level_code > maxLevel)) {
    return <Navigate to="/" replace />;
  }

  return children;
}

export default LevelRoute;
