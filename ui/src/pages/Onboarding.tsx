import { useNavigate, useSearchParams } from "react-router-dom";
import { UserCheck } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import ProfileForm from "../components/ProfileForm";
import { panel, panelTitle, btnPrimary } from "../components/styles";

export default function Onboarding() {
  const { signedIn, me, refreshMe } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const returnTo = params.get("return_to") ?? "/app";

  if (!signedIn) {
    return (
      <div className={panel} data-testid="onboarding-signed-out">
        <h1 className={panelTitle}>Account Required</h1>
        <p className="text-sm font-bold text-gray-800 mb-4">
          Please sign in to complete your profile setup.
        </p>
        <button
          type="button"
          className={btnPrimary}
          onClick={() => navigate("/login")}
        >
          Sign in
        </button>
      </div>
    );
  }

  return (
    <div className={`max-w-2xl mx-auto ${panel}`} data-testid="onboarding-page">
      <div className="flex items-center gap-2 mb-2">
        <span className="p-1.5 bg-blue-600 rounded-md text-white">
          <UserCheck size={20} />
        </span>
        <h1 className="text-xl font-black text-black uppercase tracking-wide">
          Welcome · Profile Setup
        </h1>
      </div>
      <p className="text-sm font-bold text-gray-800 mb-6">
        Answer five quick one-tap questions to calibrate integrity checks for your organization.
      </p>

      <ProfileForm
        initial={me?.profile ?? null}
        submitLabel="Save profile and continue"
        onSaved={async () => {
          await refreshMe();
          navigate(returnTo, { replace: true });
        }}
      />
    </div>
  );
}
