import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, TenderSummary } from "../api/client";
import {
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  Loader2,
} from "lucide-react";

const riskBadge = (level: string) => {
  const map: Record<string, { bg: string; text: string; icon: JSX.Element }> = {
    high: {
      bg: "bg-red-100 border-red-300",
      text: "text-red-800",
      icon: <ShieldAlert size={14} />,
    },
    medium: {
      bg: "bg-yellow-100 border-yellow-300",
      text: "text-yellow-800",
      icon: <AlertTriangle size={14} />,
    },
    low: {
      bg: "bg-green-100 border-green-300",
      text: "text-green-800",
      icon: <CheckCircle2 size={14} />,
    },
  };
  const s = map[level] ?? map["low"];
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${s.bg} ${s.text}`}
    >
      {s.icon} {level.toUpperCase()}
    </span>
  );
};

const decisionBadge = (decision: string) => {
  const map: Record<string, string> = {
    escalate: "bg-red-600 text-white",
    review: "bg-yellow-500 text-white",
    clear: "bg-green-600 text-white",
  };
  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
        map[decision] ?? "bg-gray-200 text-gray-800"
      }`}
    >
      {decision}
    </span>
  );
};

export default function TenderList() {
  const [tenders, setTenders] = useState<TenderSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getTenders()
      .then((res) => setTenders(res.data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-gray-400" size={32} />
      </div>
    );

  if (error)
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
        Error loading tenders: {error}
      </div>
    );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900">
        Tender Integrity Dashboard
      </h1>

      {tenders.length === 0 ? (
        <p className="text-gray-500">No tenders found.</p>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tender ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Decision
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tenders.map((t) => (
                <tr
                  key={t.tender_id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-6 py-4">
                    <Link
                      to={`/tender/${t.tender_id}`}
                      className="text-blue-600 hover:text-blue-800 font-mono font-medium"
                    >
                      {t.tender_id}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    <Link to={`/tender/${t.tender_id}`} className="hover:underline">
                      {t.title}
                    </Link>
                  </td>
                  <td className="px-6 py-4">{riskBadge(t.risk_level)}</td>
                  <td className="px-6 py-4">{decisionBadge(t.decision)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

