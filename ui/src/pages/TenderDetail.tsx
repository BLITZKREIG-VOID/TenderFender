import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type { AnalysisResponse, GraphResponse, RegenerateResponse } from "../api/client";
import RiskCard from "../components/RiskCard";
import ClausePanel from "../components/ClausePanel";
import GraphPanel from "../components/GraphPanel";
import DecisionPanel from "../components/DecisionPanel";
import SourceTag from "../components/SourceTag";
import RegeneratePanel from "../components/RegeneratePanel";
import ChatPanel from "../components/ChatPanel";
import { ErrorCard } from "../components/UIStates";
import { Skeleton, PanelSkeleton } from "../components/Skeleton";
import { ArrowLeft, RefreshCw, FileText, ExternalLink, Network } from "lucide-react";

export default function TenderDetail() {
  const { id } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [regen, setRegen] = useState<RegenerateResponse | null>(null);
  const [showing, setShowing] = useState<"shared" | "user">("shared");

  const fetchData = (showLoading = true) => {
    if (!id) return;
    if (showLoading) setLoading(true);
    setError(null);

    Promise.all([api.getAnalysis(id), api.getGraph(id)])
      .then(([analysisRes, graphRes]) => {
        setAnalysis(analysisRes.data);
        setGraphData(graphRes.data);
      })
      .catch((err) => {
        const msg =
          err?.response?.data?.error ||
          err?.message ||
          `Failed to load analysis for tender ${id}. Make sure the backend server is active.`;
        setError(msg);
      })
      .finally(() => {
        setLoading(false);
        setIsRefreshing(false);
      });
  };

  useEffect(() => {
    fetchData(true);
    setRegen(null);
    setShowing("shared");
  }, [id]);

  // Persisted decision; throws a readable message so the clause panel can show it (e.g. 503 read-only store).
  const decide = async (call: () => Promise<unknown>) => {
    setIsRefreshing(true);
    try {
      await call();
      fetchData(false); // reload quietly
    } catch (err: unknown) {
      setIsRefreshing(false);
      const e = err as { response?: { data?: { detail?: { error?: string } } }; message?: string };
      throw new Error(e?.response?.data?.detail?.error ?? e?.message ?? "Could not save the decision");
    }
  };

  const handleConfirm = async (atomId: string) => {
    if (!id) return;
    await decide(() => api.confirmAtom(id, atomId));
  };

  const handleReject = async (atomId: string, note: string) => {
    if (!id) return;
    await decide(() => api.rejectAtom(id, atomId, note));
  };

  if (loading) {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-busy="true"
        className="space-y-6"
      >
        <span className="sr-only">Loading tender analysis for {id}...</span>

        <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b-2 border-gray-300">
          <Skeleton className="h-10 w-56" />
          <Skeleton className="h-10 w-40" />
        </div>

        <PanelSkeleton />
        <PanelSkeleton />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PanelSkeleton />
          <PanelSkeleton />
        </div>

        <PanelSkeleton />
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div>
        <Link
          to="/app"
          className="inline-flex items-center gap-2 text-base font-black text-black hover:text-blue-700 mb-6 px-3 py-1.5 rounded-lg border-2 border-black bg-white shadow-2xs focus:outline-hidden focus:ring-4 focus:ring-blue-600"
        >
          <ArrowLeft size={18} /> Back to Registry
        </Link>
        <ErrorCard
          title={`Error Retrieving Tender ${id}`}
          error={error ?? "Tender analysis artifact not found on the server."}
          onRetry={() => fetchData(true)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Navigation & Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b-2 border-gray-300">
        <Link
          to="/app"
          className="inline-flex items-center gap-2 text-sm sm:text-base font-black text-black hover:text-white hover:bg-black px-4 py-2 rounded-lg border-2 border-black bg-white shadow-2xs focus:outline-hidden focus:ring-4 focus:ring-blue-600 transition-colors cursor-pointer"
        >
          <ArrowLeft size={18} />
          <span>Back to Tender Registry</span>
        </Link>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setIsRefreshing(true);
              fetchData(false);
            }}
            disabled={isRefreshing}
            className="inline-flex items-center gap-2 text-xs sm:text-sm font-black text-black bg-white hover:bg-gray-100 px-3.5 py-2 rounded-lg border-2 border-black shadow-2xs focus:outline-hidden focus:ring-4 focus:ring-blue-600 transition-all cursor-pointer disabled:opacity-50"
            title="Refresh Analysis"
          >
            <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />
            <span>Refresh State</span>
          </button>
          <span className="font-mono text-sm sm:text-base font-black bg-black text-white px-3 py-1.5 rounded-lg border-2 border-black">
            ID: {id}
          </span>
        </div>
      </div>

      {/* Main Title Banner */}
      <div className="bg-white p-6 rounded-xl border-4 border-gray-900 shadow-md">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-blue-100 border-2 border-blue-900 rounded-lg text-blue-900 mt-1 shrink-0">
            <FileText size={24} />
          </div>
          <div>
            <span className="text-xs font-black uppercase tracking-widest text-gray-700">
              Procurement Audit Record
            </span>
            <h1 className="text-2xl sm:text-3xl font-black text-black tracking-tight mt-0.5 leading-snug">
              {analysis.fused.title}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm font-bold text-gray-900">
              <SourceTag source={analysis.source} />
              {analysis.source === "real" && analysis.source_url && (
                <a
                  href={analysis.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-blue-800 underline decoration-2 hover:text-blue-950"
                >
                  <ExternalLink size={14} /> Source: {analysis.source_url}
                </a>
              )}
              {analysis.source === "real" && analysis.source_portal && (
                <span>Portal: {analysis.source_portal}</span>
              )}
              {analysis.source === "real" && analysis.retrieved && (
                <span>Retrieved: {analysis.retrieved}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Prominent Attribution Banner for Real Tenders */}
      {analysis.source === "real" && analysis.attribution && (
        <div
          data-testid="real-tender-attribution"
          className="bg-amber-50 border-4 border-amber-500 rounded-xl p-4 text-amber-950 font-bold text-sm shadow-sm flex items-start gap-3"
        >
          <span className="text-amber-800 shrink-0 font-black uppercase tracking-wider text-xs bg-amber-200 px-2 py-0.5 rounded border border-amber-600">
            Notice
          </span>
          <span className="leading-relaxed">{analysis.attribution}</span>
        </div>
      )}
      {/* Top: Risk Card */}
      <RiskCard fused={analysis.fused} />

      {/* Main Grid: Clauses + Graph */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Clause panel */}
        <ClausePanel
          rules={analysis.rules}
          clauses={analysis.clauses}
          onConfirm={handleConfirm}
          onReject={handleReject}
          atomStatus={analysis.atom_status}
        />

        {/* Right: Graph panel */}
        {analysis.fused.network_check?.status === "not_applicable" ? (
          <div
            data-testid="network-check-na"
            className="bg-white rounded-xl shadow-md border-4 border-gray-900 p-6 text-black flex flex-col gap-3"
          >
            <h2 className="text-xl font-black flex items-center gap-2 uppercase tracking-wide border-b-2 border-gray-300 pb-3">
              <Network size={24} /> Network Check
            </h2>
            <p className="text-base font-bold text-gray-900">
              Network check: needs bid data (post-award)
            </p>
            <p className="text-sm font-bold text-gray-700">
              No vendor or bidder graph is evaluated for a real tender before award, so there is no ring or
              linked-vendor result to show.
            </p>
          </div>
        ) : (
          <GraphPanel data={graphData} />
        )}
      </div>

      {/* Bottom: re-generation with the user's own model, then the decision panel */}
      <RegeneratePanel
        tenderId={analysis.fused.tender_id}
        result={regen}
        showing={showing}
        onResult={setRegen}
        onShow={setShowing}
      />
      <div className="mt-6">
        <DecisionPanel
          fused={
            regen && showing === "user"
              ? {
                  ...analysis.fused,
                  reasoning: regen.reasoning,
                  recommended_actions: regen.recommended_actions,
                  citations: regen.citations,
                  decision_source: regen.decision_source,
                }
              : analysis.fused
          }
          passages={analysis.passages}
        />
      </div>

      <ChatPanel tenderId={analysis.fused.tender_id} passages={analysis.passages} />
    </div>
  );
}
