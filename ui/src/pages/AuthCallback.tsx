import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { exchangeCode } from "../auth/pkce";
import { panel, panelTitle, errorBox, btnPrimary } from "../components/styles";

export default function AuthCallback() {
  const { config, configured, completeSignIn } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!config) return; // waiting for config to load

    if (!configured) {
      setError("Authentication is not configured on this server.");
      return;
    }

    const cognitoError = params.get("error_description") ?? params.get("error");
    if (cognitoError) {
      setError(`Sign-in error from provider: ${cognitoError}`);
      return;
    }

    const code = params.get("code");
    const state = params.get("state");

    if (!code || !state) {
      setError("Missing code or state parameter in authorization response.");
      return;
    }

    let active = true;

    async function handleExchange() {
      try {
        const result = await exchangeCode(config!, code!, state!);
        if (!active) return;
        const user = await completeSignIn(result.id_token, result.access_token, result.expires_in);
        if (!active) return;

        const target = result.return_to && result.return_to !== "/" ? result.return_to : "/app";
        // If the user has not completed onboarding, direct them to /onboarding
        if (!user?.profile) {
          navigate(`/onboarding?return_to=${encodeURIComponent(target)}`, { replace: true });
        } else {
          navigate(target, { replace: true });
        }
      } catch (err: unknown) {
        if (!active) return;
        const msg = err instanceof Error ? err.message : "Failed to complete authentication.";
        setError(msg);
      }
    }

    void handleExchange();

    return () => {
      active = false;
    };
  }, [config, configured, params, completeSignIn, navigate]);

  return (
    <div className={panel} data-testid="auth-callback">
      <h1 className={panelTitle}>Completing Sign-In</h1>
      {error ? (
        <div className="space-y-4">
          <div role="alert" className={errorBox}>
            {error}
          </div>
          <Link to="/login" className={btnPrimary}>
            Try signing in again
          </Link>
        </div>
      ) : (
        <p className="flex items-center gap-2 text-sm font-bold text-gray-800">
          <Loader2 size={18} className="animate-spin text-blue-600" /> Verifying security credentials…
        </p>
      )}
    </div>
  );
}
