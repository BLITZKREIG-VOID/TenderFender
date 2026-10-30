import type { FusedData } from "../api/client";
import { ShieldAlert, AlertTriangle, CheckCircle2, AlertOctagon } from "lucide-react";

interface Props {
  fused: FusedData;
}

export default function RiskCard({ fused }: Props) {
  const riskLevel = fused.risk_level?.toLowerCase();
  const decision = fused.decision?.toLowerCase();

  // High contrast color mappings for projector readability:
  // Low: Green, Medium: Orange, High: Red
  const riskBadgeStyles: Record<string, string> = {
    high: "bg-red-700 text-white border-2 border-red-900 shadow-sm",
    medium: "bg-orange-600 text-white border-2 border-orange-800 shadow-sm",
    low: "bg-green-700 text-white border-2 border-green-900 shadow-sm",
  };

  const decisionBadgeStyles: Record<string, string> = {
    escalate: "bg-red-700 text-white border-2 border-red-900 shadow-sm",
    review: "bg-orange-600 text-white border-2 border-orange-800 shadow-sm",
    clear: "bg-green-700 text-white border-2 border-green-900 shadow-sm",
  };

  const cardBorderAndHeader: Record<string, { border: string; headerBg: string; text: string }> = {
    high: {
      border: "border-red-600",
      headerBg: "bg-red-50",
      text: "text-red-950",
    },
    medium: {
      border: "border-orange-500",
      headerBg: "bg-orange-50",
      text: "text-orange-950",
    },
    low: {
      border: "border-green-600",
      headerBg: "bg-green-50",
      text: "text-green-950",
    },
  };

  const currentTheme = cardBorderAndHeader[riskLevel] || cardBorderAndHeader.low;

  return (
    <div
      className={`rounded-xl border-4 ${currentTheme.border} bg-white shadow-md overflow-hidden text-black`}
    >
      {/* Top Banner with Risk Level and Decision Badges */}
      <div
        className={`${currentTheme.headerBg} px-6 py-4 border-b-2 ${currentTheme.border} flex flex-wrap items-center justify-between gap-4`}
      >
        <div className="flex items-center gap-3">
          {riskLevel === "high" ? (
            <ShieldAlert size={34} className="text-red-700 shrink-0" />
          ) : riskLevel === "medium" ? (
            <AlertTriangle size={34} className="text-orange-600 shrink-0" />
          ) : (
            <CheckCircle2 size={34} className="text-green-700 shrink-0" />
          )}
          <div>
            <h2 className="text-xs font-black tracking-widest text-gray-800 uppercase">
              Tender Risk Assessment
            </h2>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-2xl font-black text-black tracking-tight">
                STATUS:
              </span>
              <span
                className={`inline-block px-3 py-1 rounded text-base font-black uppercase tracking-wider ${
                  riskBadgeStyles[riskLevel] || "bg-gray-800 text-white"
                }`}
              >
                RISK: {fused.risk_level}
              </span>
              <span
                className={`inline-block px-3 py-1 rounded text-base font-black uppercase tracking-wider ${
                  decisionBadgeStyles[decision] || "bg-gray-800 text-white"
                }`}
              >
                DECISION: {fused.decision}
              </span>
            </div>
          </div>
        </div>

        {/* Tender ID display */}
        <div className="font-mono text-sm bg-black text-white px-3 py-1.5 rounded font-bold">
          {fused.tender_id}
        </div>
      </div>

      {/* Card Body */}
      <div className="p-6 space-y-4">
        {/* Summary */}
        {fused.summary && (
          <div className="text-base text-gray-950 font-medium leading-relaxed bg-gray-50 p-4 rounded-lg border-2 border-gray-300">
            {fused.summary}
          </div>
        )}

        {/* Linked Vendors Section */}
        {fused.linked_vendors && fused.linked_vendors.length > 0 && (
          <div className="border-2 border-black rounded-lg p-4 bg-yellow-50/70">
            <h3 className="text-xs font-black uppercase tracking-wider text-black mb-2 flex items-center gap-1.5">
              <AlertOctagon size={16} className="text-red-700 shrink-0" />
              Flagged & Linked Vendors ({fused.linked_vendors.length})
            </h3>
            <div className="divide-y divide-gray-300">
              {fused.linked_vendors.map((vendor, idx) => (
                <div
                  key={`${vendor.vendor_id}-${idx}`}
                  className="py-2.5 first:pt-1 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-base font-black px-2.5 py-1 bg-black text-white rounded">
                      {vendor.vendor_id}
                    </span>
                    {vendor.ring_id && (
                      <span className="font-mono text-xs font-bold px-2 py-0.5 bg-red-800 text-white rounded">
                        Ring: {vendor.ring_id}
                      </span>
                    )}
                  </div>
                  <div className="text-sm font-semibold text-gray-900 bg-white px-3 py-1 rounded border border-gray-300 shadow-2xs">
                    <span className="text-gray-600 font-normal">Reason: </span>
                    <span className="font-bold text-red-950">
                      {vendor.reason.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CRITICAL Mandatory Disclaimer */}
        <div className="mt-4 p-4 bg-gray-900 text-white rounded-lg border-2 border-black shadow-inner">
          <p className="text-xs font-bold uppercase tracking-wider text-amber-300 mb-0.5">
            Mandatory Disclaimer
          </p>
          <p className="text-sm font-bold text-white tracking-wide">
            Risk indicators only; not a finding of wrongdoing. Recommendation requires human review.
          </p>
        </div>
      </div>
    </div>
  );
}
