import { useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { panel, panelTitle, link } from "../components/styles";

export default function Login() {
  const { config, configured, signedIn, login } = useAuth();
  const [params] = useSearchParams();
  const returnTo = params.get("return_to") ?? "/";

  useEffect(() => {
    if (signedIn) {
      window.location.replace(returnTo);
      return;
    }
    if (configured) {
      void login(returnTo);
    }
  }, [configured, signedIn, returnTo, login]);

  if (!config) {
    return (
      <div className={panel} data-testid="login-loading">
        <h1 className={panelTitle}>Sign In</h1>
        <p className="flex items-center gap-2 text-sm font-bold text-gray-800">
          <Loader2 size={18} className="animate-spin text-blue-600" /> Connecting to authentication service…
        </p>
      </div>
    );
  }

  if (!configured) {
    return (
      <div className={panel} data-testid="login-unconfigured">
        <h1 className={panelTitle}>Sign In</h1>
        <p className="text-sm font-bold text-gray-800 mb-4">
          Authentication is not configured on this environment (Cognito User Pool ID or Client ID not set).
          The public demo is fully browsable without signing in.
        </p>
        <Link to="/" className={link}>
          Return to tender list
        </Link>
      </div>
    );
  }

  return (
    <div className={panel} data-testid="login-redirecting">
      <h1 className={panelTitle}>Sign In</h1>
      <p className="flex items-center gap-2 text-sm font-bold text-gray-800">
        <Loader2 size={18} className="animate-spin text-blue-600" /> Redirecting to secure login…
      </p>
    </div>
  );
}
