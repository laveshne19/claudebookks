import "@/App.css";
import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import { Toaster } from "@/components/ui/sonner";
import useSilentLocationPing from "@/hooks/useSilentLocationPing";

import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Customers from "@/pages/Customers";
import CustomerDetail from "@/pages/CustomerDetail";
import Sales from "@/pages/Sales";
import Accounts from "@/pages/Accounts";
import Schemes from "@/pages/Schemes";
import Reports from "@/pages/Reports";
import Admin from "@/pages/Admin";
import Notifications from "@/pages/Notifications";
import RouteMap from "@/pages/RouteMap";
import AIRoute from "@/pages/AIRoute";
import Attendance from "@/pages/Attendance";
import ViewerDashboard from "@/pages/ViewerDashboard";

function DashboardRouter() {
  const { user } = useAuth();
  if (user?.role === "viewer") return <ViewerDashboard />;
  return <Dashboard />;
}

function BackgroundLocation() {
  const { user } = useAuth();
  // Only ping for staff that actually move (sales, managers); admins/accounts/viewer skip
  const enabled = !!user && (user.role === "sales" || user.role === "manager");
  useSilentLocationPing(enabled);
  return null;
}

function App() {
  // Register service worker once
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/service-worker.js").catch(() => {});
    }
  }, []);

  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <BackgroundLocation />
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<ProtectedRoute><DashboardRouter /></ProtectedRoute>} />
            <Route path="/customers" element={<ProtectedRoute><Customers /></ProtectedRoute>} />
            <Route path="/customers/:id" element={<ProtectedRoute><CustomerDetail /></ProtectedRoute>} />
            <Route path="/sales" element={<ProtectedRoute><Sales /></ProtectedRoute>} />
            <Route path="/accounts" element={<ProtectedRoute><Accounts /></ProtectedRoute>} />
            <Route path="/schemes" element={<ProtectedRoute><Schemes /></ProtectedRoute>} />
            <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
            <Route path="/admin" element={<ProtectedRoute roles={["super_admin","admin"]}><Admin /></ProtectedRoute>} />
            <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
            <Route path="/map" element={<ProtectedRoute><RouteMap /></ProtectedRoute>} />
            <Route path="/route" element={<ProtectedRoute><AIRoute /></ProtectedRoute>} />
            <Route path="/attendance" element={<ProtectedRoute><Attendance /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          <Toaster position="top-right" />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
