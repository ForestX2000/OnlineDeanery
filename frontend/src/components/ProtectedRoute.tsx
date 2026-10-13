import { Navigate, useLocation } from "react-router-dom";
import { useAppStore } from "@/store/useAppStore";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}