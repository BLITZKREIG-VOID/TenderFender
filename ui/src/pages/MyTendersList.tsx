import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Trash2, FileText, Loader2, ExternalLink } from "lucide-react";
import { api, apiError, describeError, type MyTenderSummary } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { panel, panelTitle, btnPrimary, errorBox } from "../components/styles";

export default function MyTendersList() {
  const { signedIn, configured, login } = useAuth();
  const [tenders, setTenders] = useState<MyTenderSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchTenders = async () => {
    if (!signedIn) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMyTenders();
      setTenders(data);
    } catch (err) {
      setError(describeError(apiError(err, "Failed to load your compiled tenders")));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchTenders();
  }, [signedIn]);

  const handleDelete = async (uid: string) => {
    if (!confirm(`Are you sure you want to delete tender ${uid}?`)) return;
    setDeletingId(uid);
    try {
      await api.deleteMyTender(uid);
      setTenders((prev) => prev.filter((t) => t.tender_id !== uid));
    } catch (err) {
      alert(describeError(apiError(err, "Failed to delete tender")));
    } finally {
      setDeletingId(null);
    }
  };

  if (!signedIn) {
    return (
      <div className={panel} data-testid="my-tenders-signed-out">
        <h1 className={panelTitle}>My Tenders</h1>
        <p className="text-sm font-bold text-gray-800 mb-4">
          Sign in to compile and manage your own procurement tenders.
        </p>
        {configured ? (
          <button type="button" className={btnPrimary} onClick={() => void login("/my-tenders")}>
            Sign in
          </button>
        ) : (
          <p className="text-xs font-bold text-gray-600">
            Authentication is not enabled in this environment.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="my-tenders-page">
      <div className={panel}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-gray-300 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="p-1.5 bg-black rounded-md text-white">
              <FileText size={22} />
            </span>
            <h1 className="text-xl font-black text-black uppercase tracking-wide">
              My Compiled Tenders
            </h1>
          </div>
          <Link to="/my-tenders/new" className={btnPrimary} data-testid="new-tender-btn">
            <Plus size={16} /> Compile New Tender
          </Link>
        </div>

        {error && (
          <div role="alert" className={`${errorBox} mb-4`}>
            {error}
          </div>
        )}

        {loading ? (
          <p className="flex items-center gap-2 text-sm font-bold text-gray-800 p-6 justify-center">
            <Loader2 size={20} className="animate-spin text-blue-600" /> Loading tenders…
          </p>
        ) : tenders.length === 0 ? (
          <div className="text-center py-12 px-4 border-2 border-dashed border-gray-400 rounded-lg" data-testid="empty-tenders">
            <FileText size={40} className="mx-auto text-gray-400 mb-2" />
            <p className="text-base font-bold text-gray-900 mb-1">
              No tenders compiled yet.
            </p>
            <p className="text-sm font-semibold text-gray-600 mb-4">
              Paste eligibility text from any procurement document to check integrity rules.
            </p>
            <Link to="/my-tenders/new" className={btnPrimary}>
              <Plus size={16} /> Compile a tender now
            </Link>
          </div>
        ) : (
          <div className="divide-y-2 border-2 border-gray-900 rounded-lg overflow-hidden" data-testid="my-tenders-list">
            {tenders.map((t) => (
              <div key={t.tender_id} className="p-4 bg-white flex flex-wrap items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs font-black px-2 py-0.5 bg-black text-white rounded">
                      {t.tender_id}
                    </span>
                    <h2 className="text-base font-black text-gray-950 truncate">{t.title}</h2>
                  </div>
                  <div className="text-xs font-bold text-gray-600 flex flex-wrap gap-3">
                    {t.created_at && <span>Compiled: {new Date(t.created_at).toLocaleDateString()}</span>}
                    {t.model && <span>Model: <code className="font-mono">{t.model}</code></span>}
                    {t.findings_count != null && (
                      <span className={t.findings_count > 0 ? "text-amber-800 font-black" : "text-emerald-800"}>
                        {t.findings_count} findings
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Link
                    to={`/my-tenders/${encodeURIComponent(t.tender_id)}`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 border-2 border-gray-900 rounded font-black text-xs uppercase"
                  >
                    View <ExternalLink size={12} />
                  </Link>
                  <button
                    type="button"
                    className="p-1.5 text-red-700 hover:text-red-900 hover:bg-red-50 rounded border border-transparent hover:border-red-400"
                    title="Delete tender"
                    disabled={deletingId === t.tender_id}
                    onClick={() => void handleDelete(t.tender_id)}
                    data-testid={`delete-tender-${t.tender_id}`}
                  >
                    {deletingId === t.tender_id ? (
                      <Loader2 size={16} className="animate-spin text-red-700" />
                    ) : (
                      <Trash2 size={16} />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
