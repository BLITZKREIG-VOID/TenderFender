import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { ShieldCheck, User, LogIn, LogOut } from "lucide-react";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import TenderList from "./pages/TenderList";
import TenderDetail from "./pages/TenderDetail";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import Onboarding from "./pages/Onboarding";
import ProfilePage from "./pages/ProfilePage";
import SettingsAi from "./pages/SettingsAi";
import HelpOpenRouterFree from "./pages/HelpOpenRouterFree";
import MyTendersList from "./pages/MyTendersList";
import MyTendersNew from "./pages/MyTendersNew";
import MyTenderDetail from "./pages/MyTenderDetail";

function HeaderNav() {
  const { signedIn, me, logout } = useAuth();
  const location = useLocation();


  return (
    <header className="bg-black text-white border-b-4 border-gray-900 shadow-md">
      <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <Link
          to="/"
          className="flex items-center gap-3 group focus:outline-hidden focus:ring-4 focus:ring-blue-400 rounded-lg p-1"
        >
          <div className="p-1.5 bg-blue-600 rounded-md border-2 border-white group-hover:bg-blue-500 transition-colors">
            <ShieldCheck size={26} className="text-white" />
          </div>
          <div className="flex flex-col">
            <span className="text-xl sm:text-2xl font-black tracking-tight text-white uppercase group-hover:text-blue-300 transition-colors">
              Tender Integrity Suite
            </span>
            <span className="text-xs font-bold text-gray-300 tracking-wider uppercase -mt-0.5">
              Procurement Integrity & Collusion Detection MVP
            </span>
          </div>
        </Link>

        {/* Navigation items & User menu */}
        <div className="flex flex-wrap items-center gap-3 sm:gap-4">
          <nav className="flex items-center gap-2">
            <Link
              to="/"
              className={`px-3 py-1.5 rounded text-xs font-black uppercase tracking-wider transition-colors ${
                location.pathname === "/"
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:text-white hover:bg-gray-800"
              }`}
            >
              Demo Tenders
            </Link>
            <Link
              to="/my-tenders"
              className={`px-3 py-1.5 rounded text-xs font-black uppercase tracking-wider transition-colors ${
                location.pathname.startsWith("/my-tenders")
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:text-white hover:bg-gray-800"
              }`}
            >
              My Tenders
            </Link>
            <Link
              to="/settings/ai"
              className={`px-3 py-1.5 rounded text-xs font-black uppercase tracking-wider transition-colors ${
                location.pathname.startsWith("/settings/ai")
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:text-white hover:bg-gray-800"
              }`}
            >
              AI Settings
            </Link>
            <Link
              to="/help/openrouter-free"
              className={`px-3 py-1.5 rounded text-xs font-black uppercase tracking-wider transition-colors ${
                location.pathname.startsWith("/help/openrouter-free")
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:text-white hover:bg-gray-800"
              }`}
            >
              Help
            </Link>
          </nav>

          <div className="h-5 w-px bg-gray-700 hidden sm:block" />

          {signedIn ? (
            <div className="flex items-center gap-2">
              <Link
                to="/profile"
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-gray-800 hover:bg-gray-700 text-xs font-black text-gray-200 border border-gray-600 truncate max-w-48"
                title={me?.email ?? "Profile"}
              >
                <User size={14} className="text-blue-400 shrink-0" />
                <span className="truncate">{me?.email ?? "Profile"}</span>
              </Link>
              <button
                type="button"
                onClick={logout}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-gray-900 hover:bg-gray-800 text-xs font-bold text-gray-300 hover:text-white border border-gray-700"
                title="Sign out"
              >
                <LogOut size={13} />
                <span>Out</span>
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-blue-600 hover:bg-blue-500 text-xs font-black uppercase tracking-wider text-white border border-blue-400 shadow-xs"
            >
              <LogIn size={14} />
              <span>Sign in</span>
            </Link>
          )}

          <div className="hidden lg:flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-black uppercase tracking-wider bg-gray-800 text-white border border-gray-600">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Live
            </span>
            <span className="text-xs font-mono font-bold px-2 py-1 bg-blue-950 text-blue-200 border border-blue-800 rounded">
              v2.0
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="min-h-screen bg-gray-100 text-gray-950 flex flex-col font-sans">
          <HeaderNav />

          <main className="max-w-7xl w-full mx-auto px-6 py-8 flex-1">
            <Routes>
              <Route path="/" element={<TenderList />} />
              <Route path="/tender/:id" element={<TenderDetail />} />
              <Route path="/tenders/:id" element={<TenderDetail />} />
              <Route path="/login" element={<Login />} />
              <Route path="/auth/callback" element={<AuthCallback />} />
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/settings/ai" element={<SettingsAi />} />
              <Route path="/help/openrouter-free" element={<HelpOpenRouterFree />} />
              <Route path="/my-tenders" element={<MyTendersList />} />
              <Route path="/my-tenders/new" element={<MyTendersNew />} />
              <Route path="/my-tenders/:id" element={<MyTenderDetail />} />
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
