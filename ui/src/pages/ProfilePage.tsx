import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { User, ShieldAlert, Trash2, CheckCircle2, Loader2, Gauge } from "lucide-react";
import { api, apiError, describeError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import ProfileForm from "../components/ProfileForm";
import { panel, panelTitle, btnDanger, btnPrimary, errorBox } from "../components/styles";

export default function ProfilePage() {
  const { signedIn, me, refreshMe, forgetAccountLocally } = useAuth();
  const navigate = useNavigate();
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (!signedIn || !me) {
    return (
      <div className={panel} data-testid="profile-signed-out">
        <h1 className={panelTitle}>Account Profile</h1>
        <p className="text-sm font-bold text-gray-800 mb-4">
          Please sign in to view and manage your account profile.
        </p>
        <Link to="/login" className={btnPrimary}>
          Sign in
        </Link>
      </div>
    );
  }

  const handleDelete = async () => {
    if (!deleteConfirm || deleting) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteMe();
      forgetAccountLocally();
      navigate("/", { replace: true });
    } catch (err) {
      setDeleteError(describeError(apiError(err, "Failed to delete account")));
      setDeleting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6" data-testid="profile-page">
      {/* Account Info & Usage Limits */}
      <div className={panel}>
        <div className="flex items-center gap-2 mb-4 border-b-2 border-gray-300 pb-3">
          <User size={24} className="text-blue-700" />
          <h1 className="text-xl font-black text-black uppercase tracking-wide">
            User Account
          </h1>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm mb-6">
          <div className="p-3 bg-gray-50 border-2 border-gray-300 rounded-lg">
            <span className="block text-xs font-black uppercase tracking-wider text-gray-700 mb-0.5">
              Email Address
            </span>
            <span className="font-bold text-gray-950 font-mono" data-testid="user-email">
              {me.email}
            </span>
          </div>
          <div className="p-3 bg-gray-50 border-2 border-gray-300 rounded-lg">
            <span className="block text-xs font-black uppercase tracking-wider text-gray-700 mb-0.5">
              User ID
            </span>
            <span className="font-bold text-gray-950 font-mono text-xs truncate block" data-testid="user-id">
              {me.user_id}
            </span>
          </div>
        </div>

        {/* Daily Usage Counters */}
        <div className="border-t-2 border-gray-200 pt-4">
          <h2 className="text-sm font-black uppercase tracking-wider text-gray-900 flex items-center gap-1.5 mb-3">
            <Gauge size={16} /> Daily API Usage & Quotas
          </h2>
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-white border-2 border-gray-900 rounded-lg text-center">
              <span className="text-xs font-bold text-gray-600 block">Re-generations</span>
              <span className="text-lg font-black text-gray-950">
                {me.usage.regen} <span className="text-xs font-bold text-gray-500">/ {me.limits.regen}</span>
              </span>
            </div>
            <div className="p-3 bg-white border-2 border-gray-900 rounded-lg text-center">
              <span className="text-xs font-bold text-gray-600 block">Tender Compiles</span>
              <span className="text-lg font-black text-gray-950">
                {me.usage.compile} <span className="text-xs font-bold text-gray-500">/ {me.limits.compile}</span>
              </span>
            </div>
            <div className="p-3 bg-white border-2 border-gray-900 rounded-lg text-center">
              <span className="text-xs font-bold text-gray-600 block">Chat Messages</span>
              <span className="text-lg font-black text-gray-950">
                {me.usage.chat} <span className="text-xs font-bold text-gray-500">/ {me.limits.chat}</span>
              </span>
            </div>
          </div>
          <p className="text-xs font-semibold text-gray-600 mt-2">
            Usage counters reset daily at 00:00 UTC.
          </p>
        </div>
      </div>

      {/* Edit Profile Form */}
      <div className={panel}>
        <h2 className={panelTitle}>Profile Information</h2>
        {successMsg && (
          <div
            role="status"
            className="p-3 bg-emerald-50 border-2 border-emerald-700 rounded-lg text-sm font-bold text-emerald-950 flex items-center gap-2 mb-4"
          >
            <CheckCircle2 size={18} className="text-emerald-700 shrink-0" />
            {successMsg}
          </div>
        )}
        <ProfileForm
          initial={me.profile}
          submitLabel="Save changes"
          onSaved={() => {
            void refreshMe();
            setSuccessMsg("Your profile has been saved successfully.");
            setTimeout(() => setSuccessMsg(null), 4000);
          }}
        />
      </div>

      {/* Danger Zone: Delete Account */}
      <div className="bg-red-50 rounded-xl shadow-md border-4 border-red-700 p-6 text-black" data-testid="danger-zone">
        <div className="flex items-center gap-2 mb-3 border-b-2 border-red-300 pb-2">
          <ShieldAlert size={22} className="text-red-700" />
          <h2 className="text-lg font-black text-red-950 uppercase tracking-wide">
            Danger Zone · Delete Account
          </h2>
        </div>
        <p className="text-sm font-bold text-red-950 mb-4">
          Permanently delete your TenderFender account. This immediately deletes your profile, all compiled tenders,
          and your authentication record from Cognito. This operation cannot be undone.
        </p>

        {deleteError && (
          <div role="alert" className={`${errorBox} mb-4`}>
            {deleteError}
          </div>
        )}

        <div className="space-y-4">
          <label className="flex items-start gap-3 text-sm font-bold text-red-950 cursor-pointer">
            <input
              type="checkbox"
              className="mt-0.5 w-5 h-5 accent-red-700"
              checked={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.checked)}
              data-testid="delete-confirm-checkbox"
            />
            <span>
              I understand that deleting my account is permanent and will purge all my saved data.
            </span>
          </label>

          <button
            type="button"
            className={btnDanger}
            disabled={!deleteConfirm || deleting}
            onClick={() => void handleDelete()}
            data-testid="delete-account-button"
          >
            {deleting ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Deleting account…
              </>
            ) : (
              <>
                <Trash2 size={16} /> Permanently delete my account
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
