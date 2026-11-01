import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { TenderSummary, TenderSource } from "../api/client";
import SourceTag, { sourceLabel } from "../components/SourceTag";
import { EmptyState, ErrorCard } from "../components/UIStates";
import { Skeleton } from "../components/Skeleton";
import {
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  ChevronRight,
  Building2,
} from "lucide-react";

export function TenderListSkeleton() {
  return (
    <div className="space-y-4 w-full">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex justify-between items-center p-5 bg-white border border-gray-200 rounded-xl shadow-sm">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-5 w-1/3" />
          <Skeleton className="h-8 w-28 rounded-md" />
        </div>
      ))}
    </div>
  );
}

const riskBadge = (level: string) => {
  const map: Record<string, { bg: string; text: string; icon: ReactNode }> = {
    high: {
      bg: "bg-red-700 text-white border-red-950",
      text: "text-white",
      icon: <ShieldAlert size={16} strokeWidth={2.5} />,
    },
    medium: {
      bg: "bg-orange-600 text-white border-orange-950",
      text: "text-white",
      icon: <AlertTriangle size={16} strokeWidth={2.5} />,
    },
    low: {
      bg: "bg-green-700 text-white border-green-950",
      text: "text-white",
      icon: <CheckCircle2 size={16} strokeWidth={2.5} />,
    },
  };
  const s = map[level] ?? map["low"];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs sm:text-sm font-black uppercase tracking-wider border-2 shadow-2xs ${s.bg} ${s.text}`}
    >
      {s.icon} {level.toUpperCase()}
    </span>
  );
};

const decisionBadge = (decision: string) => {
  const map: Record<string, string> = {
    escalate: "bg-red-700 text-white border-red-950",
    review: "bg-orange-600 text-white border-orange-950",
    clear: "bg-green-700 text-white border-green-950",
  };
  return (
    <span
      className={`inline-block px-3 py-1 rounded-md text-xs sm:text-sm font-black uppercase tracking-wider border-2 shadow-2xs ${
        map[decision] ?? "bg-gray-900 text-white border-black"
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
  const [filter, setFilter] = useState<"all" | TenderSource>("all");

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

  // Grouped: real tenders first, then the synthetic demo set; the filter narrows to one group.
  const groups: TenderSource[] = ["real", "synthetic_demo"];
  const shownGroups = groups.filter((g) => filter === "all" || filter === g);
  const shownCount = tenders.filter((t) => filter === "all" || t.source === filter).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b-2 border-gray-300">
        <div>
          <h1 className="text-3xl font-black text-black tracking-tight uppercase flex items-center gap-3">
            <Building2 size={32} className="text-black" />
            Tender Integrity Registry
          </h1>
          <p className="text-base font-bold text-gray-800 mt-1">
            Real-time formal rule verification and collusion graph analysis for high-value tenders.
          </p>
        </div>
        <div className="text-sm font-black text-black bg-white px-4 py-2 rounded-lg border-2 border-black shadow-2xs self-start sm:self-auto">
          Total Tenders: <span className="font-mono text-base">{tenders.length}</span>
        </div>
      </div>

      <div role="group" aria-label="Filter tenders by source" className="flex flex-wrap gap-2">
        {(["all", ...groups] as const).map((f) => (
          <button
            key={f}
            type="button"
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-md text-xs sm:text-sm font-black uppercase tracking-wider border-2 border-black cursor-pointer focus:outline-hidden focus:ring-4 focus:ring-blue-600 ${
              filter === f ? "bg-black text-white" : "bg-white text-black hover:bg-gray-100"
            }`}
          >
            {f === "all" ? "All" : sourceLabel(f)} (
            {f === "all" ? tenders.length : tenders.filter((t) => t.source === f).length})
          </button>
        ))}
      </div>

      {shownCount === 0 && (
        <p className="text-sm font-bold text-gray-800">
          No tenders in this group. Real tenders appear after <code>make pipeline-real</code>.
        </p>
      )}

      <div className="bg-white rounded-xl shadow-md border-4 border-gray-900 overflow-hidden">
        <table className="min-w-full divide-y-2 divide-gray-300 text-left">
          <thead className="bg-gray-100">
            <tr>
              <th
                scope="col"
                className="px-6 py-4 text-xs sm:text-sm font-black text-black uppercase tracking-wider"
              >
                Tender ID
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-xs sm:text-sm font-black text-black uppercase tracking-wider"
              >
                Procurement Title
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-xs sm:text-sm font-black text-black uppercase tracking-wider"
              >
                Calculated Risk
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-xs sm:text-sm font-black text-black uppercase tracking-wider"
              >
                Recommendation
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-right text-xs sm:text-sm font-black text-black uppercase tracking-wider"
              >
                Action
              </th>
            </tr>
          </thead>
          {shownGroups.map((g) => {
            const rows = tenders.filter((t) => t.source === g);
            if (rows.length === 0) return null;
            return (
          <tbody key={g} className="divide-y-2 divide-gray-200 border-t-2 border-gray-300">
            <tr className="bg-gray-100">
              <th colSpan={5} scope="colgroup" className="px-6 py-2 text-xs font-black uppercase tracking-wider text-gray-900">
                {sourceLabel(g)} ({rows.length})
              </th>
            </tr>
            {rows.map((t) => (
              <tr
                key={t.tender_id}
                className="hover:bg-blue-50/60 transition-colors group focus-within:bg-blue-50"
              >
                <td className="px-6 py-5 whitespace-nowrap">
                  <Link
                    to={`/tender/${t.tender_id}`}
                    className="inline-flex items-center font-mono font-black text-lg text-blue-700 hover:text-blue-950 underline decoration-2 rounded-md focus:outline-hidden focus:ring-4 focus:ring-blue-600 px-1 py-0.5"
                  >
                    {t.tender_id}
                  </Link>
                </td>
                <td className="px-6 py-5">
                  <Link
                    to={`/tender/${t.tender_id}`}
                    className="text-base sm:text-lg font-bold text-gray-950 hover:text-blue-900 hover:underline rounded-md focus:outline-hidden focus:ring-4 focus:ring-blue-600 block"
                  >
                    {t.title}
                  </Link>
                  <div className="mt-1">
                    <SourceTag source={t.source} />
                  </div>
                </td>
                <td className="px-6 py-5 whitespace-nowrap">{riskBadge(t.risk_level)}</td>
                <td className="px-6 py-5 whitespace-nowrap">{decisionBadge(t.decision)}</td>
                <td className="px-6 py-5 text-right whitespace-nowrap">
                  <Link
                    to={`/tender/${t.tender_id}`}
                    className="inline-flex items-center gap-1 px-4 py-2 bg-black hover:bg-gray-800 text-white font-black text-xs uppercase tracking-wider rounded-lg border-2 border-black shadow-2xs focus:outline-hidden focus:ring-4 focus:ring-blue-600 transition-all cursor-pointer"
                  >
                    <span>Inspect</span>
                    <ChevronRight size={16} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
            );
          })}
        </table>
      </div>
    </div>
  );
}
