import { useState, type FormEvent } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import { Loader2, Eye, EyeOff, AlertCircle } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { isPasswordPolicySatisfied } from "../auth/passwordPolicy";
import { PasswordChecklist } from "../components/PasswordChecklist";
import { GoogleButton } from "../components/GoogleButton";
import { panel, panelTitle, btnPrimary, input, label, errorBox, link } from "../components/styles";

export default function SignUp() {
  const { config, signedIn, signUp, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (signedIn) {
    return <Navigate to="/app" replace />;
  }

  const isPolicyMet = isPasswordPolicySatisfied(password);
  const isMatch = password === confirmPassword;
  const canSubmit = email.trim() !== "" && isPolicyMet && isMatch && !loading;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setError(null);

    try {
      await signUp(email.trim(), password);
      // Pass the email and ephemeral in-memory password to /verify
      // Password is NEVER stored to disk or localStorage/sessionStorage.
      navigate(`/verify?email=${encodeURIComponent(email.trim())}`, {
        state: { email: email.trim(), password },
      });
    } catch (err: unknown) {
      let msg = "Unable to create account. Please verify your details and try again.";
      if (err instanceof Error && err.message) {
        msg = err.message;
      } else if (typeof err === "object" && err !== null && "message" in err && typeof err.message === "string") {
        msg = err.message;
      }
      setError(msg);
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    setError(null);
    try {
      await loginWithGoogle("/app");
    } catch {
      setError("Unable to start Google authentication. Please try again.");
    }
  };

  return (
    <div className="max-w-md mx-auto py-6">
      <div className={panel}>
        <h1 className={panelTitle}>Create Account</h1>

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

        {error && (
          <div className={`${errorBox} mb-5 flex items-start gap-2.5`} role="alert">
            <AlertCircle size={18} className="text-red-700 shrink-0 mt-0.5" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate={false}>
          <div>
            <label htmlFor="signup-email" className={label}>
              Email Address
            </label>
            <input
              id="signup-email"
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
            <label htmlFor="signup-password" className={label}>
              Password
            </label>
            <div className="relative">
              <input
                id="signup-password"
                type={showPassword ? "text" : "password"}
                required
                disabled={loading}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                autoComplete="new-password"
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
            <div className="mt-2.5">
              <PasswordChecklist password={password} />
            </div>
          </div>

          <div>
            <label htmlFor="signup-confirm-password" className={label}>
              Confirm Password
            </label>
            <div className="relative">
              <input
                id="signup-confirm-password"
                type={showConfirmPassword ? "text" : "password"}
                required
                disabled={loading}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                autoComplete="new-password"
                className={`${input} pr-12 min-h-[44px]`}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                disabled={loading}
                aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                className="absolute right-1 top-1/2 -translate-y-1/2 min-h-[40px] min-w-[40px] flex items-center justify-center text-gray-600 hover:text-black rounded focus:outline-hidden focus:ring-2 focus:ring-blue-600 cursor-pointer"
              >
                {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {confirmPassword.length > 0 && !isMatch && (
              <p className="text-xs font-bold text-red-600 mt-1.5" role="alert">
                Passwords do not match.
              </p>
            )}
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
                <span>Create account</span>
              )}
            </button>
          </div>
        </form>

        <div className="mt-6 pt-4 border-t-2 border-gray-200 text-center text-sm font-bold text-gray-700">
          <span>Already have an account? </span>
          <Link to="/login" className={link}>
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
