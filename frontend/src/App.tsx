
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAppStore } from "./store/useAppStore";
import HomePage from "./pages/HomePage";
import UploadPage from "./pages/UploadPage";
import { DocumentResult } from "./components/DocumentResult";

function ResultPage() {
  const result = useAppStore((state) => state.result);

  if (!result) {
    return <Navigate to="/upload" replace />;
  }

  return (
    <main className="min-h-screen bg-[#F7F8FA] px-5 py-10">
      <div className="mx-auto max-w-5xl">
        <DocumentResult />
      </div>
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/result" element={<ResultPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
