import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import LevelRoute from "./LevelRoute";
import LoginPage from "../pages/LoginPage";
import ActivateAccountPage from "../pages/ActivateAccountPage";
import DashboardPage from "../pages/DashboardPage";
import UsersAdminPage from "../pages/UsersAdminPage";
import RecordsPage from "../pages/RecordsPage";
import RecordDetailPage from "../pages/RecordDetailPage";
import IntakeFormPage from "../pages/IntakeFormPage";
import DeletionRequestsPage from "../pages/DeletionRequestsPage";
import ArcoPage from "../pages/ArcoPage";
import AuditPage from "../pages/AuditPage";
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
        path="/records/new"
        element={
          <ProtectedRoute>
            <IntakeFormPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/records"
        element={
          <ProtectedRoute>
            <RecordsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/records/:id"
        element={
          <ProtectedRoute>
            <RecordDetailPage />
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
        path="/deletion-requests"
        element={
          <ProtectedRoute>
            <LevelRoute maxLevel={2}>
              <DeletionRequestsPage />
            </LevelRoute>
          </ProtectedRoute>
        }
      />

      <Route
        path="/arco"
        element={
          <ProtectedRoute>
            <LevelRoute maxLevel={3}>
              <ArcoPage />
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
            <LevelRoute maxLevel={2}>
              <SigningSetupPage />
            </LevelRoute>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default AppRouter;
