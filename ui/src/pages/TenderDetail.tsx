import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type { AnalysisResponse, GraphResponse } from "../api/client";
import RiskCard from "../components/RiskCard";
import ClausePanel from "../components/ClausePanel";
import GraphPanel from "../components/GraphPanel";
import DecisionPanel from "../components/DecisionPanel";
import { ErrorCard } from "../components/UIStates";
import { Skeleton, PanelSkeleton } from "../components/Skeleton";
import { ArrowLeft, RefreshCw, FileText } from "lucide-react";

export default function TenderDetail() {
  const { id } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  // ── Tabbed interface state ──────────────────────────────────────
  const [activeTab, setActiveTab] = useState<'overview' | 'proofs' | 'graph'>(
    "overview"
  );

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
  }, [id]);

  const handleConfirm = async (atomId: string) => {
    if (!id) return;
    setIsRefreshing(true);
    try {
      await api.confirmAtom(id, atomId);
      fetchData(false); // reload quietly
    } catch (err: unknown) {
      console.error("Confirmation error:", err);
      setIsRefreshing(false);
      // Propagate so the clause panel can roll back its optimistic state.
      throw err;
    }
  };

  // ── Tab bar ─────────────────────────────────────────────────────
  const tabBar = (
    <div className="flex border-b border-gray-200">
      <button
        type="button"
        className={`flex-1 rounded-t-lg px-4 py-2 text-sm font-medium ${
          activeTab === "overview"
            ? "text-indigo-700 border-indigo-700 border-b-2"
            : "text-slate-500 hover:text-slate-700 transition-colors"
        }`}
        onClick={() => setActiveTab("overview")}
      >
        Overview
      </button>
      <button
        type="button"
        className={`flex-1 rounded-t-lg px-4 py-2 text-sm font-medium ${
          activeTab === "proofs"
            ? "text-indigo-700 border-indigo-700 border-b-2"
            : "text-slate-500 hover:text-slate-700 transition-colors"
        }`}
        onClick={() => setActiveTab("proofs")}
      >
        Proofs
      </button>
      <button
        type="button"
        className={`flex-1 rounded-t-lg px-4 py-2 text-sm font-medium ${
          activeTab === "graph"
            ? "text-indigo-700 border-indigo-700 border-b-2"
            : "text-slate-500 hover:text-slate-700 transition-colors"
        }`}
        onClick={() => setActiveTab("graph")}
      >
        Graph
      </button>
    </div>
  );

  if (loading) {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-busy="true"
        className="space-y-6"
      >
        <span className="sr-only">Loading tender analysis for {id}...</span>

        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 pb-2">
          <Skeleton className="h-10 w-56" />
          <Skeleton className="h-10 w-40" />
        </div>

        <PanelSkeleton />
        <PanelSkeleton />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
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
          to="/"
          className="mb-6 inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base font-medium text-slate-700 shadow-sm hover:bg-slate-100 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
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

  // ── Tab content renderers ───────────────────────────────────────
  const overviewContent = (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Left: Risk Card */}
      <RiskCard fused={analysis.fused} disclaimer={analysis.fused.disclaimer} />

      {/* Right: Decision Panel */}
      <DecisionPanel fused={analysis.fused} passages={analysis.passages} />
    </div>
  );

  const proofsContent = (
    <ClausePanel
      rules={analysis.rules}
      clauses={analysis.clauses}
      onConfirm={handleConfirm}
      isDanger={
        analysis.fused.risk_level?.toLowerCase() === "high" ||
        analysis.fused.decision?.toLowerCase() === "escalate"
      }
    />
  );

  const graphContent = (
    <GraphPanel data={graphData} isDanger={
      analysis.fused.risk_level?.toLowerCase() === "high" ||
      analysis.fused.decision?.toLowerCase() === "escalate"
    } />
  );

  const tabContent = {
    overview: overviewContent,
    proofs: proofsContent,
    graph: graphContent,
  }[activeTab];

  return (
    <div className="space-y-6">
      {/* Top Navigation & Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 pb-2">
        <Link
          to="/"
          className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-100 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
        >
          <ArrowLeft size={18} />
          <span>Back to Tender Registry</span>
        </Link>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              if (id) api.invalidateTender(id);
              setIsRefreshing(true);
              fetchData(false);
            }}
            disabled={isRefreshing}
            className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-gray-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-100 focus:outline-hidden focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            title="Refresh Analysis"
          >
            <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />
            <span>Refresh State</span>
          </button>
          <span className="rounded-lg bg-slate-800 px-3 py-1.5 font-mono text-sm font-medium text-white">
            ID: {id}
          </span>
        </div>
      </div>

      {/* Main Title Banner */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <div className="mt-1 shrink-0 rounded-lg border border-blue-100 bg-blue-50 p-2 text-blue-600">
            <FileText size={24} />
          </div>
          <div>
            <span className="text-xs font-medium text-slate-500">
              Procurement Audit Record
            </span>
            <h1 className="mt-1 text-2xl font-semibold leading-snug tracking-tight text-slate-900 sm:text-3xl">
              {analysis.fused.title}
            </h1>
          </div>
        </div>
      </div>

      {/* Tabbed content area */}
      <div className="mt-4">
        {tabBar}
        {/* Content below the tab bar has no extra top margin when on overview;
           other tabs will have their own spacing handled inside. */}
        {tabContent}
      </div>

      {/* Bottom: Decision panel (only show on overview tab) */}
      {/* Already included in overviewContent above */}
    </div>
  );
}