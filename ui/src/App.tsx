import { useState } from "react";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { ShieldCheck, User, LogIn, LogOut, Menu, X, ArrowRight } from "lucide-react";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";

// Public pages
import Landing from "./pages/Landing";
import SignUp from "./pages/SignUp";
import Verify from "./pages/Verify";
import Login from "./pages/Login";
import ForgotPassword from "./pages/ForgotPassword";
import AuthCallback from "./pages/AuthCallback";
import DemoList from "./pages/DemoList";
import DemoDetail from "./pages/DemoDetail";
import HelpOpenRouterFree from "./pages/HelpOpenRouterFree";
import NotFound from "./pages/NotFound";

// Protected pages
import AppDashboard from "./pages/AppDashboard";
import TenderDetail from "./pages/TenderDetail";
import Onboarding from "./pages/Onboarding";
import ProfilePage from "./pages/ProfilePage";
import SettingsAi from "./pages/SettingsAi";
import MyTendersList from "./pages/MyTendersList";
import MyTendersNew from "./pages/MyTendersNew";
import MyTenderDetail from "./pages/MyTenderDetail";

function HeaderNav() {
  const { signedIn, me, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isTendersActive =
    location.pathname === "/app" ||
    location.pathname.startsWith("/tender") ||
    location.pathname.startsWith("/tenders");
  const isMyTendersActive = location.pathname.startsWith("/my-tenders");
  const isSettingsActive = location.pathname.startsWith("/settings");

  return (
    <header className="bg-black text-white border-b-4 border-gray-900 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-4">
        {/* Brand / Logo */}
        <Link
          to={signedIn ? "/app" : "/"}
          className="flex items-center gap-3 group focus:outline-hidden focus:ring-4 focus:ring-blue-400 rounded-lg p-1 min-h-[44px]"
        >
          <div className="p-1.5 bg-blue-600 rounded-md border-2 border-white group-hover:bg-blue-500 transition-colors">
            <ShieldCheck size={26} className="text-white" />
          </div>
          <div className="flex flex-col">
            <span className="text-lg sm:text-2xl font-black tracking-tight text-white uppercase group-hover:text-blue-300 transition-colors">
              Tender Integrity Suite
            </span>
            <span className="text-[10px] sm:text-xs font-bold text-gray-300 tracking-wider uppercase -mt-0.5">
              Procurement Integrity & Collusion Detection MVP
            </span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-3">
          {signedIn ? (
            <>
              <nav className="flex items-center gap-1.5">
                <Link
                  to="/app"
                  className={`min-h-[44px] inline-flex items-center px-3.5 py-2 rounded text-xs font-black uppercase tracking-wider transition-colors ${
                    isTendersActive
                      ? "bg-blue-600 text-white"
                      : "text-gray-300 hover:text-white hover:bg-gray-800"
                  }`}
                >
                  Tenders
                </Link>
                <Link
                  to="/my-tenders"
                  className={`min-h-[44px] inline-flex items-center px-3.5 py-2 rounded text-xs font-black uppercase tracking-wider transition-colors ${
                    isMyTendersActive
                      ? "bg-blue-600 text-white"
                      : "text-gray-300 hover:text-white hover:bg-gray-800"
                  }`}
                >
                  My tenders
                </Link>
                <Link
                  to="/settings/ai"
                  className={`min-h-[44px] inline-flex items-center px-3.5 py-2 rounded text-xs font-black uppercase tracking-wider transition-colors ${
                    isSettingsActive
                      ? "bg-blue-600 text-white"
                      : "text-gray-300 hover:text-white hover:bg-gray-800"
                  }`}
                >
                  Settings
                </Link>
              </nav>

              <div className="h-5 w-px bg-gray-700" />

              <div className="flex items-center gap-2">
                <Link
                  to="/profile"
                  className="min-h-[44px] inline-flex items-center gap-2 px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 text-xs font-black text-gray-200 border border-gray-600 truncate max-w-56"
                  title={me?.email ?? "Profile"}
                >
                  <User size={15} className="text-blue-400 shrink-0" />
                  <span className="truncate">{me?.email ?? "Profile"}</span>
                </Link>
                <button
                  type="button"
                  onClick={logout}
                  className="min-h-[44px] inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-gray-900 hover:bg-gray-800 text-xs font-bold text-gray-300 hover:text-white border border-gray-700 cursor-pointer"
                  title="Sign out"
                >
                  <LogOut size={14} />
                  <span>Out</span>
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-3">
              <Link
                to="/login"
                className="min-h-[44px] inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gray-900 hover:bg-gray-800 text-xs font-black uppercase tracking-wider text-gray-200 border border-gray-700"
              >
                <LogIn size={15} />
                <span>Sign in</span>
              </Link>
              <Link
                to="/signup"
                className="min-h-[44px] inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-black uppercase tracking-wider text-white border border-blue-400 shadow-xs"
              >
                <span>Create account</span>
                <ArrowRight size={14} />
              </Link>
            </div>
          )}
        </div>

        {/* Mobile menu toggle button */}
        <div className="flex md:hidden items-center gap-2">
          {signedIn ? (
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="min-h-[44px] min-w-[44px] flex items-center justify-center p-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 hover:text-white"
              aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="min-h-[44px] inline-flex items-center px-3 py-2 rounded bg-gray-900 text-xs font-black uppercase tracking-wider text-gray-200 border border-gray-700"
              >
                Sign in
              </Link>
              <Link
                to="/signup"
                className="min-h-[44px] inline-flex items-center px-3 py-2 rounded bg-blue-600 text-xs font-black uppercase tracking-wider text-white border border-blue-400"
              >
                Join
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Collapsible Navigation (Signed In) */}
      {signedIn && mobileMenuOpen && (
        <div className="md:hidden border-t border-gray-800 bg-gray-950 px-4 py-4 space-y-3">
          <nav className="flex flex-col space-y-2">
            <Link
              to="/app"
              onClick={() => setMobileMenuOpen(false)}
              className={`min-h-[44px] flex items-center px-4 py-2.5 rounded text-sm font-black uppercase tracking-wider ${
                isTendersActive ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-gray-900"
              }`}
            >
              Tenders
            </Link>
            <Link
              to="/my-tenders"
              onClick={() => setMobileMenuOpen(false)}
              className={`min-h-[44px] flex items-center px-4 py-2.5 rounded text-sm font-black uppercase tracking-wider ${
                isMyTendersActive ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-gray-900"
              }`}
            >
              My tenders
            </Link>
            <Link
              to="/settings/ai"
              onClick={() => setMobileMenuOpen(false)}
              className={`min-h-[44px] flex items-center px-4 py-2.5 rounded text-sm font-black uppercase tracking-wider ${
                isSettingsActive ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-gray-900"
              }`}
            >
              Settings
            </Link>
            <Link
              to="/profile"
              onClick={() => setMobileMenuOpen(false)}
              className="min-h-[44px] flex items-center gap-2 px-4 py-2.5 rounded text-sm font-bold text-gray-300 hover:bg-gray-900"
            >
              <User size={16} className="text-blue-400" />
              <span>{me?.email ?? "Profile"}</span>
            </Link>
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false);
                logout();
              }}
              className="min-h-[44px] flex items-center gap-2 px-4 py-2.5 rounded text-sm font-bold text-red-400 hover:bg-gray-900 text-left"
            >
              <LogOut size={16} />
              <span>Sign out</span>
            </button>
          </nav>
        </div>
      )}
    </header>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="min-h-screen bg-gray-100 text-gray-950 flex flex-col font-sans">
          <HeaderNav />

          <main className="max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 flex-1">
            <Routes>
              {/* Public & Authentication Flow */}
              <Route path="/" element={<Landing />} />
              <Route path="/signup" element={<SignUp />} />
              <Route path="/verify" element={<Verify />} />
              <Route path="/login" element={<Login />} />
              <Route path="/forgot" element={<ForgotPassword />} />
              <Route path="/auth/callback" element={<AuthCallback />} />

              {/* Demo Preview (Anyone) */}
              <Route path="/demo" element={<DemoList />} />
              <Route path="/demo/tender/:id" element={<DemoDetail />} />

              {/* Help Center (Anyone) */}
              <Route path="/help/openrouter-free" element={<HelpOpenRouterFree />} />
              <Route path="/help/*" element={<HelpOpenRouterFree />} />

              {/* Protected Workspace (Signed In) */}
              <Route
                path="/app"
                element={
                  <ProtectedRoute>
                    <AppDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/onboarding"
                element={
                  <ProtectedRoute>
                    <Onboarding />
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
                path="/settings/ai"
                element={
                  <ProtectedRoute>
                    <SettingsAi />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/my-tenders"
                element={
                  <ProtectedRoute>
                    <MyTendersList />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/my-tenders/new"
                element={
                  <ProtectedRoute>
                    <MyTendersNew />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/my-tenders/:id"
                element={
                  <ProtectedRoute>
                    <MyTenderDetail />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/tender/:id"
                element={
                  <ProtectedRoute>
                    <TenderDetail />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/tenders/:id"
                element={
                  <ProtectedRoute>
                    <TenderDetail />
                  </ProtectedRoute>
                }
              />

              {/* Unknown 404 Route */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>

          <footer className="bg-white border-t-2 border-gray-300 py-4 mt-auto">
            <div className="max-w-7xl mx-auto px-6 text-center text-xs font-bold text-gray-700">
              Tender Integrity Verification Platform • High-Contrast Projector Display Mode Enabled
            </div>
          </footer>
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
