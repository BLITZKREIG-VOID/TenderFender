import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, AnalysisResponse, GraphResponse } from "../api/client";
import RiskCard from "../components/RiskCard";
import ClausePanel from "../components/ClausePanel";
import GraphPanel from "../components/GraphPanel";
import DecisionPanel from "../components/DecisionPanel";
import { ArrowLeft, Loader2 } from "lucide-react";

export default function TenderDetail() {
  const { id } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = () => {
    if (!id) return;
    setLoading(true);
    Promise.all([api.getAnalysis(id), api.getGraph(id)])
      .then(([analysisRes, graphRes]) => {
        setAnalysis(analysisRes.data);
        setGraphData(graphRes.data);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  const handleConfirm = async (atomId: string) => {
    if (!id) return;
    await api.confirmAtom(id, atomId);
    fetchData(); // re-fetch to reflect updated status
  };

  if (loading)
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-gray-400" size={32} />
      </div>
    );

  if (error || !analysis)
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
        {error ?? "Analysis data not available."}
      </div>
    );

  return (
    <div>
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 mb-4"
      >
        <ArrowLeft size={16} /> Back to list
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-1">
        {analysis.fused.title}
      </h1>
      <p className="text-sm text-gray-500 font-mono mb-6">{id}</p>

      {/* Top: Risk card */}
      <RiskCard fused={analysis.fused} />

      {/* Main content: clauses + graph */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
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

