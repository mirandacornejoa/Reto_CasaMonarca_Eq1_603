import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import AdminRoute from "./AdminRoute";
import LoginPage from "../pages/LoginPage";
import ActivateAccountPage from "../pages/ActivateAccountPage";
import AdminDashboardPage from "../pages/AdminDashboardPage";
import UsersAdminPage from "../pages/UsersAdminPage";

function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/activate" element={<ActivateAccountPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AdminDashboardPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin/users"
        element={
          <ProtectedRoute>
            <AdminRoute>
              <UsersAdminPage />
            </AdminRoute>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default AppRouter;
