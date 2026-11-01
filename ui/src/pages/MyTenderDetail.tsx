import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";
import { api, apiError, describeError, type CompileResponse } from "../api/client";
import { panel, link, errorBox } from "../components/styles";

export default function MyTenderDetail() {
  const { id } = useParams<{ id: string }>();
  const [tender, setTender] = useState<CompileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let active = true;
    setLoading(true);
    setError(null);

    api
      .getMyTender(id)
      .then((res) => {
        if (active) setTender(res.data);
      })
      .catch((err) => {
        if (active) setError(describeError(apiError(err, "Failed to load tender details.")));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [id]);

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="my-tender-detail-page">
      <div>
        <Link to="/my-tenders" className={`inline-flex items-center gap-1 text-sm ${link}`}>
          <ArrowLeft size={16} /> Back to My Tenders
        </Link>
      </div>

      {loading ? (
        <div className={panel}>
          <p className="flex items-center gap-2 text-sm font-bold text-gray-800 p-6 justify-center">
            <Loader2 size={20} className="animate-spin text-blue-600" /> Loading tender details…
          </p>
        </div>
      ) : error ? (
        <div className={panel}>
          <div role="alert" className={errorBox}>
            {error}
          </div>
        </div>
      ) : tender ? (
        <div className="space-y-6">
          <div className={panel}>
            <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-gray-300 pb-3 mb-4">
              <div>
                <span className="font-mono text-xs font-black px-2.5 py-1 bg-black text-white rounded mb-1 inline-block">
                  {tender.tender_id}
                </span>
                <h1 className="text-xl font-black text-black uppercase tracking-wide">
                  {tender.title || tender.tender_id}
                </h1>
              </div>
              {tender.created_at && (
                <span className="text-xs font-bold text-gray-600">
                  Compiled on {new Date(tender.created_at).toLocaleString()}
                </span>
              )}
            </div>

            {/* Findings */}
            <div className="mb-6">
              <h2 className="text-sm font-black uppercase tracking-wider text-black mb-3">
                Risk Indicators & Findings ({tender.findings?.length ?? 0})
              </h2>
              {tender.findings && tender.findings.length > 0 ? (
                <div className="space-y-3">
                  {tender.findings.map((f, i) => (
                    <div key={i} className="p-4 bg-amber-50 border-2 border-amber-700 rounded-lg">
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="font-mono text-xs font-black uppercase px-2 py-0.5 bg-amber-200 text-amber-950 rounded">
                          {f.type}
                        </span>
                        <span className="text-xs font-black uppercase px-2 py-0.5 bg-gray-900 text-white rounded">
                          {f.severity}
                        </span>
                      </div>
                      <p className="font-bold text-gray-950 text-sm">{f.explanation}</p>
                      {f.clause_ids && f.clause_ids.length > 0 && (
                        <span className="text-xs font-mono font-bold text-gray-700 mt-2 block">
                          Referenced Clauses: {f.clause_ids.join(", ")}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm font-bold text-emerald-800 p-4 bg-emerald-50 border-2 border-emerald-500 rounded-lg">
                  No risk indicators found in this compiled tender.
                </p>
              )}
            </div>

            {/* Clauses */}
            <div className="border-t-2 border-gray-200 pt-4">
              <h2 className="text-sm font-black uppercase tracking-wider text-black mb-3">
                Extracted Clauses ({tender.clauses?.length ?? 0})
              </h2>
              <div className="space-y-2">
                {tender.clauses?.map((c) => (
                  <div key={c.clause_id} className="p-3 bg-gray-50 border border-gray-300 rounded text-xs">
                    <span className="font-mono font-black text-gray-900 mr-2">{c.clause_id}:</span>
                    <span className="font-bold text-gray-800">{c.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
