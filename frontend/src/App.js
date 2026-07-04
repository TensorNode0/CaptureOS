import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Spinner } from "./components/ui";
import Shell from "./components/Shell";

import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import VerifyEmail from "./pages/VerifyEmail";
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import Intelligence from "./pages/Intelligence";
import Opportunities from "./pages/Opportunities";
import OpportunityDetail from "./pages/OpportunityDetail";
import Capability from "./pages/Capability";
import ProposalWorkspace from "./pages/ProposalWorkspace";
import Profile from "./pages/Profile";
import Admin from "./pages/Admin";
import Settings from "./pages/Settings";

function FullLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner size={28} className="text-cyan" />
    </div>
  );
}

function Protected({ children }) {
  const { user, activeOrg } = useAuth();
  const location = useLocation();
  if (user === null) return <FullLoader />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (!user.organizations || user.organizations.length === 0)
    return <Navigate to="/onboarding" replace />;
  if (!activeOrg) return <FullLoader />;
  return <Shell>{children}</Shell>;
}

function PublicOnly({ children }) {
  const { user } = useAuth();
  if (user === null) return <FullLoader />;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="space-bg" />
      <div className="starfield" />
      <Toaster
        position="top-right"
        theme="dark"
        toastOptions={{
          style: {
            background: "var(--bg-elev)",
            border: "1px solid var(--line)",
            color: "var(--text)",
          },
        }}
      />
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
          <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />
          <Route path="/forgot-password" element={<PublicOnly><ForgotPassword /></PublicOnly>} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
          <Route path="/intelligence" element={<Protected><Intelligence /></Protected>} />
          <Route path="/opportunities" element={<Protected><Opportunities /></Protected>} />
          <Route path="/opportunities/:id" element={<Protected><OpportunityDetail /></Protected>} />
          <Route path="/opportunities/:id/capability" element={<Protected><Capability /></Protected>} />
          <Route path="/opportunities/:id/proposal" element={<Protected><ProposalWorkspace /></Protected>} />
          <Route path="/profile" element={<Protected><Profile /></Protected>} />
          <Route path="/admin" element={<Protected><Admin /></Protected>} />
          <Route path="/settings" element={<Protected><Settings /></Protected>} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
