import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { STAFF, useAuth } from "./auth";
import Admin from "./pages/Admin";
import Alerts from "./pages/Alerts";
import CaseDetail from "./pages/CaseDetail";
import Cases from "./pages/Cases";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import SubmitTransaction from "./pages/SubmitTransaction";
import TransactionDetail from "./pages/TransactionDetail";
import Transactions from "./pages/Transactions";
import AMLTesting from "./pages/AMLTesting.jsx";

// Only lets a signed-in user through, and only if their role is allowed.
function Protected({ children, roles }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/transactions" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/transactions" replace /> : <Login />}
      />

      <Route
        path="/"
        element={
          <Protected roles={STAFF}>
            <Dashboard />
          </Protected>
        }
      />
      <Route
        path="/transactions"
        element={
          <Protected>
            <Transactions />
          </Protected>
        }
      />
      <Route
        path="/transactions/:id"
        element={
          <Protected>
            <TransactionDetail />
          </Protected>
        }
      />  
      <Route
        path="/aml-testing"
        element={
          <Protected roles={["ADMIN"]}>
            <AMLTesting />
          </Protected>
        }
      />
      <Route
        path="/submit"
        element={
          <Protected>
            <SubmitTransaction />
          </Protected>
        }
      />
      <Route
        path="/alerts"
        element={
          <Protected roles={STAFF}>
            <Alerts />
          </Protected>
        }
      />
      <Route
        path="/cases"
        element={
          <Protected roles={STAFF}>
            <Cases />
          </Protected>
        }
      />
      <Route
        path="/cases/:id"
        element={
          <Protected roles={STAFF}>
            <CaseDetail />
          </Protected>
        }
      />
      <Route
        path="/admin"
        element={
          <Protected roles={["ADMIN", "COMPLIANCE"]}>
            <Admin />
          </Protected>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
