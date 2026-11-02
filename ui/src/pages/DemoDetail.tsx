import { useEffect, useState } from "react";
import { useParams, Link, Navigate } from "react-router-dom";
import { api, type AnalysisResponse, type GraphResponse } from "../api/client";
import RiskCard from "../components/RiskCard";
import ClausePanel from "../components/ClausePanel";
import GraphPanel from "../components/GraphPanel";
import DecisionPanel from "../components/DecisionPanel";
import SourceTag from "../components/SourceTag";
import { DemoBanner } from "../components/DemoBanner";
import { ErrorCard } from "../components/UIStates";
import { Skeleton, PanelSkeleton } from "../components/Skeleton";
import { ArrowLeft, ExternalLink, Network } from "lucide-react";

export default function DemoDetail() {
  const { id } = useParams<{ id: string }>();

  // Spec: Real tender ids under /demo → redirect to /login
  if (!id || !id.startsWith("T-")) {
    const next = encodeURIComponent(id ? `/tender/${id}` : "/app");
    return <Navigate to={`/login?next=${next}`} replace />;
  }

  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = () => {
    setLoading(true);
    setError(null);

    Promise.all([
      api.getAnalysis(id),
      api.getGraph(id).catch(() => ({ data: null })),
    ])
      .then(([analysisRes, graphRes]) => {
        setAnalysis(analysisRes.data);
        setGraphData(graphRes.data);
      })
      .catch((err) => {
        let msg = `Unable to load demo analysis for ${id}.`;
        if (err instanceof Error && err.message) {
          msg = err.message;
        } else if (typeof err === "object" && err !== null && "message" in err && typeof err.message === "string") {
          msg = err.message;
        }
        setError(msg);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-6">
        <DemoBanner />
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-10 w-3/4" />
        </div>
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
      <div className="space-y-6">
        <DemoBanner />
        <ErrorCard
          title="Demo Analysis Not Found"
          error={error || "Could not retrieve tender analysis"}
          onRetry={fetchDetail}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <DemoBanner />

      {/* Top bar with back navigation and meta */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b-2 border-gray-300">
        <div className="flex items-center gap-4">
          <Link
            to="/demo"
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white text-black font-black text-xs uppercase tracking-wider rounded-lg border-2 border-black shadow-2xs hover:bg-gray-100 transition-colors min-h-[44px]"
          >
            <ArrowLeft size={16} />
            <span>Demo Registry</span>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl sm:text-3xl font-black font-mono text-black">
                {analysis.fused.tender_id}
              </h1>
              <SourceTag source={analysis.source} />
            </div>
            <p className="text-sm font-bold text-gray-700 mt-0.5">{analysis.fused.title}</p>
          </div>
        </div>

        {analysis.source_url && (
          <div className="flex items-center gap-2">
            <a
              href={analysis.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-white text-black font-bold text-xs rounded-lg border-2 border-black hover:bg-gray-100 min-h-[44px]"
            >
              <span>Source</span>
              <ExternalLink size={14} />
            </a>
          </div>
        )}
      </div>

      {/* Primary Risk Card */}
      <RiskCard fused={analysis.fused} />

      {/* Middle Grid: Clauses & Collusion Graph */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ClausePanel
          rules={analysis.rules}
          clauses={analysis.clauses}
          atomStatus={analysis.atom_status}
          onConfirm={async () => {}}
          onReject={async () => {}}
          readOnly
        />

        {analysis.fused.network_check?.status === "not_applicable" ? (
          <div
            data-testid="network-check-na"
            className="bg-white rounded-xl shadow-md border-4 border-gray-900 p-6 flex flex-col justify-between"
          >
            <div>
              <h2 className="text-xl font-black text-black flex items-center gap-2 uppercase tracking-wide border-b-2 border-gray-300 pb-3 mb-4">
                <Network size={22} className="text-gray-500" /> Collusion Network Graph
              </h2>
              <div className="p-4 bg-gray-100 border-2 border-gray-300 rounded-lg text-sm font-bold text-gray-800">
                Network analysis not applicable for single-bidder or synthetic benchmark tenders.
              </div>
            </div>
          </div>
        ) : (
          <GraphPanel data={graphData} />
        )}
      </div>

      {/* Read-only Decision & Citations Panel (NO AI panels in demo preview) */}
      <div className="mt-6">
        <DecisionPanel fused={analysis.fused} passages={analysis.passages} />
      </div>
    </div>
  );
}
