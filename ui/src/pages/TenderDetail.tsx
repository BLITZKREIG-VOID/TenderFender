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
    }
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
          to="/"
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
          to="/"
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
          </div>
        </div>
      </div>

      {/* Top: Risk Card */}
      <RiskCard fused={analysis.fused} />

      {/* Main Grid: Clauses + Graph */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Clause panel */}
        <ClausePanel
          rules={analysis.rules}
          clauses={analysis.clauses}
          onConfirm={handleConfirm}
        />

        {/* Right: Graph panel */}
        <GraphPanel data={graphData} />
      </div>

      {/* Bottom: Decision panel */}
      <div className="mt-6">
        <DecisionPanel fused={analysis.fused} />
      </div>
    </div>
  );
}
