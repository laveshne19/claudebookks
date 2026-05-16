import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import { Toaster } from "@/components/ui/sonner";

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

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/customers" element={<ProtectedRoute roles={["super_admin","admin","manager","sales"]}><Customers /></ProtectedRoute>} />
            <Route path="/customers/:id" element={<ProtectedRoute roles={["super_admin","admin","manager","sales"]}><CustomerDetail /></ProtectedRoute>} />
            <Route path="/sales" element={<ProtectedRoute roles={["super_admin","admin","manager","sales"]}><Sales /></ProtectedRoute>} />
            <Route path="/accounts" element={<ProtectedRoute roles={["super_admin","admin","manager","accounts"]}><Accounts /></ProtectedRoute>} />
            <Route path="/schemes" element={<ProtectedRoute><Schemes /></ProtectedRoute>} />
            <Route path="/reports" element={<ProtectedRoute roles={["super_admin","admin","manager","accounts"]}><Reports /></ProtectedRoute>} />
            <Route path="/admin" element={<ProtectedRoute roles={["super_admin","admin"]}><Admin /></ProtectedRoute>} />
            <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
            <Route path="/route" element={<ProtectedRoute><RouteMap /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          <Toaster position="top-right" />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
