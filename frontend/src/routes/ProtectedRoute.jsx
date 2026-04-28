import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

/**
 * Protects child routes — redirects to /login if no token.
 * Uses user.id as React key to force full remount of children
 * when user changes (prevents cross-user state contamination).
 */
function ProtectedRoute({ children }) {
  const { token, user, loading } = useAuth();

  if (loading) {
    return <p className="container">Cargando sesión...</p>;
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // Key by user.id: when user changes, React destroys and recreates
  // ALL children, guaranteeing no stale state from the previous user.
  return <div key={user?.id || "anon"}>{children}</div>;
}

export default ProtectedRoute;
