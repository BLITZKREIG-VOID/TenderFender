import { useState, useEffect, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams, Navigate } from "react-router-dom";
import { Loader2, AlertCircle, CheckCircle2, RotateCw } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { panel, panelTitle, btnPrimary, btnSecondary, input, label, errorBox, link } from "../components/styles";

export default function Verify() {
  const { signedIn, confirmSignUp, resendCode, signInWithSrp } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  // Prefill email from navigation state or URL query parameter
  const stateEmail =
    typeof location.state === "object" && location.state !== null && "email" in location.state
      ? String(location.state.email)
      : "";
  const initialEmail = stateEmail || params.get("email") || "";

  // Password in ephemeral memory (only from state, never stored)
  const ephemeralPassword =
    typeof location.state === "object" && location.state !== null && "password" in location.state
      ? String(location.state.password)
      : "";

  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendNotice, setResendNotice] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);

  if (signedIn) {
    return <Navigate to="/app" replace />;
  }

  // 30-second cooldown timer for resend code
  useEffect(() => {
    if (cooldown <= 0) return;
    const interval = setInterval(() => {
      setCooldown((c) => (c > 0 ? c - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldown]);

  const canSubmit = email.trim() !== "" && code.trim().length === 6 && !loading;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setError(null);
    setResendNotice(null);

    try {
      await confirmSignUp(email.trim(), code.trim());

      // If the password is still in memory, sign in automatically
      if (ephemeralPassword) {
        try {
          await signInWithSrp(email.trim(), ephemeralPassword);
          navigate("/app", { replace: true });
          return;
        } catch {
          // If auto sign-in fails, fall through to login screen
        }
      }

      // No password in memory or auto sign-in deferred: go to login with success notice
      navigate("/login", {
        replace: true,
        state: {
          notice: "Email verified successfully! Please sign in with your credentials.",
          email: email.trim(),
        },
      });
    } catch (err: unknown) {
      let msg = "Verification failed. Please check the code and try again.";
      if (err instanceof Error && err.message) {
        msg = err.message;
      } else if (typeof err === "object" && err !== null && "message" in err && typeof err.message === "string") {
        msg = err.message;
      }
      setError(msg);
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0 || resending || !email.trim()) return;

    setResending(true);
    setError(null);
    setResendNotice(null);

    try {
      await resendCode(email.trim());
      setCooldown(30);
      setResendNotice("A new 6-digit verification code has been sent to your email.");
    } catch (err: unknown) {
      let msg = "Unable to resend code. Please try again.";
      if (err instanceof Error && err.message) {
        msg = err.message;
      } else if (typeof err === "object" && err !== null && "message" in err && typeof err.message === "string") {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-6">
      <div className={panel}>
        <h1 className={panelTitle}>Verify Your Account</h1>

        <p className="text-sm font-medium text-gray-700 mb-5">
          Enter the 6-digit confirmation code sent to your email address to activate your account.
        </p>

        {error && (
          <div className={`${errorBox} mb-5 flex items-start gap-2.5`} role="alert">
            <AlertCircle size={18} className="text-red-700 shrink-0 mt-0.5" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {resendNotice && (
          <div
            className="p-3 bg-emerald-50 border-2 border-emerald-700 rounded-lg text-sm font-bold text-emerald-950 mb-5 flex items-start gap-2.5"
            role="status"
          >
            <CheckCircle2 size={18} className="text-emerald-700 shrink-0 mt-0.5" aria-hidden="true" />
            <span>{resendNotice}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate={false}>
          <div>
            <label htmlFor="verify-email" className={label}>
              Email Address
            </label>
            <input
              id="verify-email"
              type="email"
              required
              disabled={loading || resending}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="officer@agency.gov.in"
              autoComplete="email"
              className={`${input} min-h-[44px]`}
            />
          </div>

          <div>
            <label htmlFor="verify-code" className={label}>
              6-Digit Verification Code
            </label>
            <input
              id="verify-code"
              type="text"
              required
              disabled={loading}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="123456"
              maxLength={6}
              inputMode="numeric"
              pattern="[0-9]{6}"
              autoComplete="one-time-code"
              className={`${input} font-mono text-center tracking-widest text-lg font-black min-h-[44px]`}
            />
          </div>

          <div className="pt-2 space-y-3">
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
                <span>Verify</span>
              )}
            </button>

            <button
              type="button"
              onClick={handleResend}
              disabled={cooldown > 0 || resending || loading || !email.trim()}
              className={`${btnSecondary} w-full min-h-[44px]`}
            >
              {resending ? (
                <>
                  <Loader2 size={16} className="animate-spin" aria-hidden="true" />
                  <span>Sending code…</span>
                </>
              ) : cooldown > 0 ? (
                <span>Resend code ({cooldown}s)</span>
              ) : (
                <>
                  <RotateCw size={16} />
                  <span>Resend code</span>
                </>
              )}
            </button>
          </div>
        </form>

        <div className="mt-6 pt-4 border-t-2 border-gray-200 text-center text-sm font-bold text-gray-700">
          <span>Remember your credentials? </span>
          <Link to="/login" className={link}>
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
