import { useState, useEffect, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams, Navigate } from "react-router-dom";
import { Loader2, Eye, EyeOff, AlertCircle, CheckCircle2, ArrowRight } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { sanitizeNext } from "../auth/passwordPolicy";
import { GoogleButton } from "../components/GoogleButton";
import { panel, panelTitle, btnPrimary, input, label, errorBox, link } from "../components/styles";
import { ACCOUNT_DELETED_STORAGE_KEY } from "../api/client";

export default function Login() {
  const { config, signedIn, signInWithSrp, loginWithGoogle } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  // Safely extract and sanitize redirect destination (relative only)
  const nextTarget = sanitizeNext(params.get("next") || params.get("return_to"), "/app");

  // Prefill email or notice passed from /verify or /forgot
  const stateObj =
    typeof location.state === "object" && location.state !== null ? location.state : {};
  const initialEmail = "email" in stateObj && typeof stateObj.email === "string" ? stateObj.email : "";
  const initialNotice = "notice" in stateObj && typeof stateObj.notice === "string" ? stateObj.notice : "";

  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isNotVerified, setIsNotVerified] = useState(false);
  const [notice] = useState<string | null>(initialNotice || null);
  useEffect(() => {
    try {
      sessionStorage.removeItem(ACCOUNT_DELETED_STORAGE_KEY);
    } catch {
      // ignore
    }
  }, []);

  if (signedIn) {
    return <Navigate to={nextTarget} replace />;
  }

  const canSubmit = email.trim() !== "" && password !== "" && !loading;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setError(null);
    setIsNotVerified(false);

    try {
      await signInWithSrp(email.trim(), password);
      navigate(nextTarget, { replace: true });
    } catch (err: unknown) {
      let msg = "Incorrect email or password.";
      let notConfirmed = false;

      if (err instanceof Error && err.message) {
        msg = err.message;
      } else if (typeof err === "object" && err !== null) {
        if ("message" in err && typeof err.message === "string") {
          msg = err.message;
        }
        if ("isNotConfirmed" in err && Boolean(err.isNotConfirmed)) {
          notConfirmed = true;
        }
        if ("code" in err && err.code === "USER_NOT_CONFIRMED") {
          notConfirmed = true;
        }
      }

      setError(msg);
      setIsNotVerified(notConfirmed);
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    setError(null);
    try {
      await loginWithGoogle(nextTarget);
    } catch {
      setError("Unable to start Google authentication. Please try again.");
    }
  };

  return (
    <div className="max-w-md mx-auto py-6">
      <div className={panel}>
        <h1 className={panelTitle}>Sign In</h1>

        {notice && (
          <div
            className="p-3 bg-emerald-50 border-2 border-emerald-700 rounded-lg text-sm font-bold text-emerald-950 mb-5 flex items-start gap-2.5"
            role="status"
          >
            <CheckCircle2 size={18} className="text-emerald-700 shrink-0 mt-0.5" aria-hidden="true" />
            <span>{notice}</span>
          </div>
        )}

        {error && (
          <div className={`${errorBox} mb-5 space-y-2`} role="alert">
            <div className="flex items-start gap-2.5">
              <AlertCircle size={18} className="text-red-700 shrink-0 mt-0.5" aria-hidden="true" />
              <span>{error}</span>
            </div>
            {isNotVerified && (
              <div className="pt-1">
                <Link
                  to={`/verify?email=${encodeURIComponent(email.trim())}`}
                  className="inline-flex items-center gap-1.5 text-xs font-black uppercase tracking-wider text-blue-900 underline hover:text-black"
                >
                  <span>Verify your email now</span>
                  <ArrowRight size={14} />
                </Link>
              </div>
            )}
          </div>
        )}

        {config?.google_enabled && (
          <div className="space-y-4 mb-6">
            <GoogleButton onClick={handleGoogle} disabled={loading} label="Continue with Google" />
            <div className="relative flex items-center justify-center">
              <div className="border-t-2 border-gray-300 w-full" />
              <span className="bg-white px-3 text-xs font-black uppercase tracking-wider text-gray-500 absolute">
                or with email
              </span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate={false}>
          <div>
            <label htmlFor="login-email" className={label}>
              Email Address
            </label>
            <input
              id="login-email"
              type="email"
              required
              disabled={loading}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="officer@agency.gov.in"
              autoComplete="email"
              className={`${input} min-h-[44px]`}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label htmlFor="login-password" className={`${label} mb-0`}>
                Password
              </label>
              <Link
                to="/forgot"
                className="text-xs font-bold text-blue-800 underline hover:text-blue-950"
              >
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                required
                disabled={loading}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                autoComplete="current-password"
                className={`${input} pr-12 min-h-[44px]`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                disabled={loading}
                aria-label={showPassword ? "Hide password" : "Show password"}
                className="absolute right-1 top-1/2 -translate-y-1/2 min-h-[40px] min-w-[40px] flex items-center justify-center text-gray-600 hover:text-black rounded focus:outline-hidden focus:ring-2 focus:ring-blue-600 cursor-pointer"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={!canSubmit}
              className={`${btnPrimary} w-full min-h-[44px]`}
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" aria-hidden="true" />
                  <span>Working…</span>
                </>
              ) : (
                <span>Sign in</span>
              )}
            </button>
          </div>
        </form>

        <div className="mt-6 pt-4 border-t-2 border-gray-200 text-center text-sm font-bold text-gray-700">
          <span>New here? </span>
          <Link to="/signup" className={link}>
            Create account
          </Link>
        </div>
      </div>
    </div>
  );
}
