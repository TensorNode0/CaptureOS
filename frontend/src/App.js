import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Spinner } from "./components/ui";
import Shell from "./components/Shell";
import { canSeeDashboard } from "./lib/helpers";

import Home from "./pages/marketing/Home";
import Why from "./pages/marketing/Why";
import FeaturesPage from "./pages/marketing/Features";
import ResourcesPage from "./pages/marketing/Resources";
import About from "./pages/marketing/About";
import Article from "./pages/marketing/resources/Article";
import { BlogIndex, BlogPost } from "./pages/marketing/Blog";
import Privacy from "./pages/marketing/Privacy";
import Reviews from "./pages/marketing/Reviews";
import Contact from "./pages/marketing/Contact";
import CookieConsent from "./components/CookieConsent";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import VerifyEmail from "./pages/VerifyEmail";
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import Intelligence from "./pages/Intelligence";
import Opportunities from "./pages/Opportunities";
import Proposals from "./pages/Proposals";
import CompetitiveAnalysis from "./pages/CompetitiveAnalysis";
import SharedWithMe from "./pages/SharedWithMe";
import PrivateCapital from "./pages/venture/PrivateCapital";
import InvestmentDeals from "./pages/venture/InvestmentDeals";
import Accelerators from "./pages/venture/Accelerators";
import AcceleratorApplications from "./pages/venture/AcceleratorApplications";
import OpportunityDetail from "./pages/OpportunityDetail";
import Capability from "./pages/Capability";
import ProposalWorkspace from "./pages/ProposalWorkspace";
import Profile from "./pages/Profile";
import Admin from "./pages/Admin";
import Settings from "./pages/Settings";
import DiskStorage from "./pages/DiskStorage";
import BillingSuccess from "./pages/BillingSuccess";
import Pricing from "./pages/marketing/Pricing";
import RequireTier from "./components/RequireTier";
import { SubscriptionProvider } from "./lib/billing";

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

// Public root: marketing home for visitors, app for signed-in users.
function RootRedirect() {
  const { user } = useAuth();
  if (user === null) return <FullLoader />;
  return <Navigate to={user ? "/dashboard" : "/home"} replace />;
}

// Dashboards are for the admin and the capture manager; contributors land on
// the opportunities pipeline; subcontractors only see their shared items.
function DashboardGate({ children }) {
  const { activeOrg } = useAuth();
  if (activeOrg?.role === "subcontractor") return <Navigate to="/shared" replace />;
  if (activeOrg && !canSeeDashboard(activeOrg.role))
    return <Navigate to="/opportunities" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className="space-bg" />
      <div className="starfield" />
      <CookieConsent />
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
        <SubscriptionProvider>
        <Routes>
          <Route path="/home" element={<Home />} />
          <Route path="/why" element={<Why />} />
          <Route path="/features" element={<FeaturesPage />} />
          <Route path="/resources" element={<ResourcesPage />} />
          <Route path="/resources/:slug" element={<Article />} />
          <Route path="/blog" element={<BlogIndex />} />
          <Route path="/blog/:slug" element={<BlogPost />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/reviews" element={<Reviews />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/about" element={<About />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
          <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />
          <Route path="/forgot-password" element={<PublicOnly><ForgotPassword /></PublicOnly>} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/dashboard" element={<Protected><DashboardGate><Dashboard /></DashboardGate></Protected>} />
          <Route path="/intelligence" element={<Protected><Intelligence /></Protected>} />
          <Route path="/opportunities" element={<Protected><Opportunities /></Protected>} />
          <Route path="/proposals" element={<Protected><RequireTier minTier="full" feature="Federal Proposals"><Proposals /></RequireTier></Protected>} />
          <Route path="/competitive-analysis" element={<Protected><CompetitiveAnalysis /></Protected>} />
          <Route path="/shared" element={<Protected><SharedWithMe /></Protected>} />
          <Route path="/private-capital" element={<Protected><PrivateCapital /></Protected>} />
          <Route path="/investment-deals" element={<Protected><RequireTier minTier="full" feature="Investment Deals"><InvestmentDeals /></RequireTier></Protected>} />
          <Route path="/accelerators" element={<Protected><Accelerators /></Protected>} />
          <Route path="/accelerator-applications" element={<Protected><RequireTier minTier="full" feature="Accelerator Applications"><AcceleratorApplications /></RequireTier></Protected>} />
          <Route path="/opportunities/:id" element={<Protected><OpportunityDetail /></Protected>} />
          <Route path="/opportunities/:id/capability" element={<Protected><Capability /></Protected>} />
          <Route path="/opportunities/:id/proposal" element={<Protected><RequireTier minTier="full" feature="Federal Proposals"><ProposalWorkspace /></RequireTier></Protected>} />
          <Route path="/profile" element={<Protected><Profile /></Protected>} />
          <Route path="/admin" element={<Protected><Admin /></Protected>} />
          <Route path="/settings" element={<Protected><Settings /></Protected>} />
          <Route path="/disk-storage" element={<Protected><RequireTier minTier="full" feature="Company Disk Storage"><DiskStorage /></RequireTier></Protected>} />
          <Route path="/billing/success" element={<Protected><BillingSuccess /></Protected>} />
          <Route path="/" element={<RootRedirect />} />
          <Route path="*" element={<RootRedirect />} />
        </Routes>
        </SubscriptionProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
