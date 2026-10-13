import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAppStore } from "./store/useAppStore";
import HomePage from "./pages/HomePage";
import UploadPage from "./pages/UploadPage";
import LoginPage from "./pages/LoginPage";

import ProfilePage from "./pages/ProfilePage";
import { DocumentResult } from "./components/DocumentResult";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import DocumentDetailsPage from "./pages/DocumentDetailsPage";
import { ThemeProvider } from "./context/ThemeProvider";



function ResultPage() {
  const result = useAppStore((state) => state.result);
  if (!result) return <Navigate to="/upload" replace />;

  return (
    <div className="px-5 py-10">
      <div className="mx-auto max-w-5xl">
        <DocumentResult />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
    <BrowserRouter>
      <Routes>
        
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          
         
          <Route 
            path="/upload" 
            element={
              <ProtectedRoute>
                <UploadPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/result" 
            element={
              <ProtectedRoute>
                <ResultPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/profile" 
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            } 
          />
           <Route
  path="/documents/:documentId"
  element={
    <ProtectedRoute>
      <DocumentDetailsPage />
    </ProtectedRoute>
  }
/>
          
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
    </ThemeProvider>
  );
}