import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { Toaster } from "sonner";
import { CabinetProvider } from "./lib/CabinetContext";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { UploadPage } from "./pages/Upload";
import { InvoiceDetail } from "./pages/InvoiceDetail";
import { LoginPage } from "./pages/Login";
import { RegisterPage } from "./pages/Register";
import { SettingsPage } from "./pages/Settings";
import { AdminPage } from "./pages/Admin";
import { LandingPage } from "./pages/Landing";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 10_000 },
  },
});

const router = createBrowserRouter([
  // Routes publiques
  { path: "/", element: <LandingPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  // Routes protégées (Layout redirige vers /login sans session)
  {
    element: <Layout />,
    children: [
      { path: "/dashboard", element: <Dashboard /> },
      { path: "/upload", element: <UploadPage /> },
      { path: "/invoices/:id", element: <InvoiceDetail /> },
      { path: "/settings", element: <SettingsPage /> },
      { path: "/admin", element: <AdminPage /> },
      { path: "*", element: <Navigate to="/dashboard" replace /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <CabinetProvider>
        <RouterProvider router={router} />
        <Toaster position="top-right" richColors />
      </CabinetProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
