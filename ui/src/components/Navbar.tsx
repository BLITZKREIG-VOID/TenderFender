import { User } from "lucide-react";
import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav
      className="bg-white border-b border-gray-200 sticky top-0 z-50 px-6 py-3 flex justify-between items-center"
    >
      {/* Left: Brand */}
      <div className="flex items-center gap-3">
        <User size={20} className="text-slate-400" />
        <span className="text-lg font-bold text-slate-800">TenderFender</span>
      </div>

      {/* Center: App Links */}
      <div className="hidden md:flex items-center gap-8">
        <Link
          to="/"
          className="text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors underline underline-offset-2"
        >
          Registry
        </Link>
        <Link
          to="/about"
          className="text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors underline underline-offset-2"
        >
          About
        </Link>
        <a
          href="/analytics"
          className="text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors underline underline-offset-2"
        >
          Analytics
        </a>
        <a
          href="/settings"
          className="text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors underline underline-offset-2"
        >
          Settings
        </a>
      </div>

      {/* Right: User Profile */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <div
            className="flex items-center justify-center rounded-full bg-indigo-100 text-indigo-500 text-xs font-medium"
          >
            HV
          </div>
        </div>
        <span className="text-sm font-medium text-slate-700">Welcome, Harsh</span>
      </div>
    </nav>
  );
}
