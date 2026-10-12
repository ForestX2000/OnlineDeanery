import { createBrowserRouter } from "react-router-dom";
import HomePage from "@/pages/HomePage";
import UploadPage from "@/pages/UploadPage";
import LoginPage from "@/pages/LoginPage";


export const router = createBrowserRouter([
  { path: "/", element: <HomePage /> },
  { path: "/upload", element: <UploadPage /> },
  { path: "/login", element: <LoginPage /> },
  
]);