import { Link } from "react-router-dom";
import { AlertCircle, Home, Eye, LogIn } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { panel, btnPrimary, btnSecondary } from "../components/styles";

export default function NotFound() {
  const { signedIn } = useAuth();

  return (
    <div className="max-w-xl mx-auto py-12 text-center">
      <div className={`${panel} space-y-6`}>
        <div className="w-16 h-16 rounded-full bg-red-100 border-2 border-red-700 text-red-700 flex items-center justify-center mx-auto">
          <AlertCircle size={36} />
        </div>

        <div className="space-y-2">
          <h1 className="text-3xl font-black uppercase tracking-tight text-gray-950">
            Page Not Found
          </h1>
          <p className="text-sm font-medium text-gray-700 max-w-md mx-auto">
            The page or document you requested could not be found. Check the URL or return to the main platform.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <Link
            to={signedIn ? "/app" : "/"}
            className={`${btnPrimary} w-full sm:w-auto min-h-[44px] text-xs`}
          >
            <Home size={16} />
            <span>{signedIn ? "Go to Dashboard" : "Return Home"}</span>
          </Link>

          <Link
            to="/demo"
            className={`${btnSecondary} w-full sm:w-auto min-h-[44px] text-xs`}
          >
            <Eye size={16} />
            <span>Explore Demo</span>
          </Link>

          {!signedIn && (
            <Link
              to="/login"
              className={`${btnSecondary} w-full sm:w-auto min-h-[44px] text-xs`}
            >
              <LogIn size={16} />
              <span>Sign In</span>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
