import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { TenderSummary } from "../api/client";
import { EmptyState, ErrorCard } from "../components/UIStates";
import { Skeleton } from "../components/Skeleton";
import {
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  ChevronRight,
} from "lucide-react";

export function TenderListSkeleton() {
  return (
    <div className="w-full space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-5 w-1/3" />
          <Skeleton className="h-9 w-28 rounded-lg" />
        </div>
      ))}
    </div>
  );
}

const riskBadge = (level: string) => {
  const map: Record<string, { bg: string; icon: ReactNode }> = {
    high: {
      bg: "border-red-200 bg-red-50 text-red-700",
      icon: <ShieldAlert size={14} strokeWidth={2} />,
    },
    medium: {
      bg: "border-amber-200 bg-amber-50 text-amber-700",
      icon: <AlertTriangle size={14} strokeWidth={2} />,
    },
    low: {
      bg: "border-green-200 bg-green-50 text-green-700",
      icon: <CheckCircle2 size={14} strokeWidth={2} />,
    },
  };
  const s = map[level] ?? map["low"];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${s.bg}`}
    >
      {s.icon} {level}
    </span>
  );
};

const decisionBadge = (decision: string) => {
  const map: Record<string, string> = {
    escalate: "border-red-200 bg-red-50 text-red-700",
    review: "border-amber-200 bg-amber-50 text-amber-700",
    clear: "border-green-200 bg-green-50 text-green-700",
  };
  return (
    <span
      className={`inline-block rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
        map[decision] ?? "border-gray-200 bg-slate-100 text-slate-600"
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

  const fetchTenders = () => {
    setLoading(true);
    setError(null);
    api
      .getTenders()
      .then((res) => setTenders(res.data))
      .catch((err) => {
        const msg =
          err?.response?.data?.error ||
          err?.message ||
          "Unable to connect to the Tender Integrity API server at http://localhost:8000.";
        setError(msg);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchTenders();
  }, []);

  if (loading) {
    return <TenderListSkeleton />;
  }

  if (error) {
    return (
      <ErrorCard
        title="Could Not Load Tenders"
        error={error}
        onRetry={fetchTenders}
      />
    );
  }

  if (tenders.length === 0) {
    return (
      <EmptyState
        title="No Evaluated Tenders Found"
        message="No tender records are present in the current environment. Ensure MOCK=1 or run the pipeline to generate artifacts."
        actionText="Refresh Tenders"
        onAction={fetchTenders}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 text-left">
          <thead className="bg-slate-50">
            <tr>
              <th scope="col" className="px-6 py-4 text-sm font-semibold text-slate-600">
                Tender ID
              </th>
              <th scope="col" className="px-6 py-4 text-sm font-semibold text-slate-600">
                Procurement Title
              </th>
              <th scope="col" className="px-6 py-4 text-sm font-semibold text-slate-600">
                Calculated Risk
              </th>
              <th scope="col" className="px-6 py-4 text-sm font-semibold text-slate-600">
                Recommendation
              </th>
              <th scope="col" className="px-6 py-4 text-right text-sm font-semibold text-slate-600">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {tenders.map((t) => (
              <tr
                key={t.tender_id}
                className="group transition-colors hover:bg-slate-50 focus-within:bg-slate-50"
              >
                <td className="whitespace-nowrap px-6 py-5">
                  <Link
                    to={`/tender/${t.tender_id}`}
                    className="inline-flex items-center rounded-md px-1 py-0.5 font-mono text-base font-medium text-blue-600 hover:text-blue-700 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                  >
                    {t.tender_id}
                  </Link>
                </td>
                <td className="px-6 py-5">
                  <Link
                    to={`/tender/${t.tender_id}`}
                    className="block rounded-md text-base font-medium text-slate-800 hover:text-blue-700 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                  >
                    {t.title}
                  </Link>
                </td>
                <td className="whitespace-nowrap px-6 py-5">{riskBadge(t.risk_level)}</td>
                <td className="whitespace-nowrap px-6 py-5">{decisionBadge(t.decision)}</td>
                <td className="whitespace-nowrap px-6 py-5 text-right">
                  <Link
                    to={`/tender/${t.tender_id}`}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-slate-700 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                  >
                    <span>Inspect</span>
                    <ChevronRight size={16} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
