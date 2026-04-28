import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import LevelRoute from "./LevelRoute";
import LoginPage from "../pages/LoginPage";
import ActivateAccountPage from "../pages/ActivateAccountPage";
import DashboardPage from "../pages/DashboardPage";
import UsersAdminPage from "../pages/UsersAdminPage";
import RecordsPage from "../pages/RecordsPage";
import AuditPage from "../pages/AuditPage";
import TemplatesPage from "../pages/TemplatesPage";
import TOTPSetupPage from "../pages/TOTPSetupPage";
import SigningSetupPage from "../pages/SigningSetupPage";

function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/activate" element={<ActivateAccountPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/records"
        element={
          <ProtectedRoute>
            <LevelRoute maxLevel={3}>
              <RecordsPage />
            </LevelRoute>
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin/users"
        element={
          <ProtectedRoute>
            <LevelRoute maxLevel={1}>
              <UsersAdminPage />
            </LevelRoute>
          </ProtectedRoute>
        }
      />

      <Route
        path="/audit"
        element={
          <ProtectedRoute>
            <LevelRoute maxLevel={1}>
              <AuditPage />
            </LevelRoute>
          </ProtectedRoute>
        }
      />

      <Route
        path="/templates"
        element={
          <ProtectedRoute>
            <LevelRoute maxLevel={1}>
              <TemplatesPage />
            </LevelRoute>
          </ProtectedRoute>
        }
      />

      <Route
        path="/security/totp"
        element={
          <ProtectedRoute>
            <TOTPSetupPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/security/signing"
        element={
          <ProtectedRoute>
            <SigningSetupPage />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default AppRouter;
