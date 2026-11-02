import { useState, type FormEvent } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import { Loader2, Eye, EyeOff, AlertCircle, ArrowLeft } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { isPasswordPolicySatisfied } from "../auth/passwordPolicy";
import { PasswordChecklist } from "../components/PasswordChecklist";
import { panel, panelTitle, btnPrimary, btnSecondary, input, label, errorBox, link } from "../components/styles";

export default function ForgotPassword() {
  const { signedIn, forgotPassword, confirmNewPassword } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState<1 | 2>(1);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (signedIn) {
    return <Navigate to="/app" replace />;
  }

  const isPolicyMet = isPasswordPolicySatisfied(newPassword);
  const isMatch = newPassword === confirmPassword;

  // Step 1: Request reset code
  const handleRequestCode = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || loading) return;

    setLoading(true);
    setError(null);

    try {
      await forgotPassword(email.trim());
      setStep(2);
    } catch (err: unknown) {
      let msg = "Unable to process password reset. Please try again.";
      if (err instanceof Error && err.message) {
        msg = err.message;
      } else if (typeof err === "object" && err !== null && "message" in err && typeof err.message === "string") {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Confirm new password
  const handleResetPassword = async (e: FormEvent) => {
    e.preventDefault();
    if (!code.trim() || !isPolicyMet || !isMatch || loading) return;

    setLoading(true);
    setError(null);

    try {
      await confirmNewPassword(email.trim(), code.trim(), newPassword);
      navigate("/login", {
        replace: true,
        state: {
          notice: "Password reset successfully. Sign in with your new password.",
          email: email.trim(),
        },
      });
    } catch (err: unknown) {
      let msg = "Failed to reset password. Please verify the code and try again.";
      if (err instanceof Error && err.message) {
        msg = err.message;
      } else if (typeof err === "object" && err !== null && "message" in err && typeof err.message === "string") {
        msg = err.message;
      }
      setError(msg);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-6">
      <div className={panel}>
        <h1 className={panelTitle}>Reset Password</h1>

        {error && (
          <div className={`${errorBox} mb-5 flex items-start gap-2.5`} role="alert">
            <AlertCircle size={18} className="text-red-700 shrink-0 mt-0.5" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {step === 1 ? (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-5">
              Enter the email address associated with your account. We will send you a 6-digit verification code to reset your password.
            </p>

            <form onSubmit={handleRequestCode} className="space-y-4">
              <div>
                <label htmlFor="forgot-email" className={label}>
                  Email Address
                </label>
                <input
                  id="forgot-email"
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

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={!email.trim() || loading}
                  className={`${btnPrimary} w-full min-h-[44px]`}
                >
                  {loading ? (
                    <>
                      <Loader2 size={18} className="animate-spin" aria-hidden="true" />
                      <span>Working…</span>
                    </>
                  ) : (
                    <span>Send Reset Code</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        ) : (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-5">
              Enter the 6-digit code sent to <strong className="text-gray-950 font-black">{email}</strong> and choose a new password.
            </p>

            <form onSubmit={handleResetPassword} className="space-y-4">
              <div>
                <label htmlFor="reset-code" className={label}>
                  6-Digit Verification Code
                </label>
                <input
                  id="reset-code"
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

              <div>
                <label htmlFor="reset-new-password" className={label}>
                  New Password
                </label>
                <div className="relative">
                  <input
                    id="reset-new-password"
                    type={showPassword ? "text" : "password"}
                    required
                    disabled={loading}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
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
                  <PasswordChecklist password={newPassword} />
                </div>
              </div>

              <div>
                <label htmlFor="reset-confirm-password" className={label}>
                  Confirm New Password
                </label>
                <div className="relative">
                  <input
                    id="reset-confirm-password"
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

              <div className="pt-2 space-y-3">
                <button
                  type="submit"
                  disabled={!code.trim() || !isPolicyMet || !isMatch || loading}
                  className={`${btnPrimary} w-full min-h-[44px]`}
                >
                  {loading ? (
                    <>
                      <Loader2 size={18} className="animate-spin" aria-hidden="true" />
                      <span>Working…</span>
                    </>
                  ) : (
                    <span>Reset Password</span>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setStep(1)}
                  disabled={loading}
                  className={`${btnSecondary} w-full min-h-[44px]`}
                >
                  <ArrowLeft size={16} />
                  <span>Use different email</span>
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="mt-6 pt-4 border-t-2 border-gray-200 text-center text-sm font-bold text-gray-700">
          <span>Remember your password? </span>
          <Link to="/login" className={link}>
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
