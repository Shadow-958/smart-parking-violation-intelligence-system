import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, staffOnly = false }) {
  const { currentUser, isStaff, loading } = useAuth();

  if (loading) {
    return <div className="flex h-screen items-center justify-center font-display uppercase">Loading…</div>;
  }

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  if (staffOnly && !isStaff) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
