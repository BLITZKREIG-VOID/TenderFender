import type { FusedData } from "../api/client";
import { ShieldAlert, AlertTriangle, CheckCircle2, AlertOctagon } from "lucide-react";

interface Props {
  fused: FusedData;
  /** Verbatim disclaimer from the fused payload; falls back to fused.disclaimer. */
  disclaimer?: string;
}

export default function RiskCard({ fused, disclaimer }: Props) {
  const riskLevel = fused.risk_level?.toLowerCase();
  const decision = fused.decision?.toLowerCase();
  const disclaimerText = disclaimer ?? fused.disclaimer;

  // Red budget: only high risk or an escalate decision may use red accents.
  const isDanger = riskLevel === "high" || decision === "escalate";

  // Background + border tint per risk level so the card always signals the zone.
  const riskBackground: Record<string, string> = {
    high: "bg-red-50 border-red-200",
    medium: "bg-amber-50 border-amber-200",
    low: "bg-emerald-50 border-emerald-200",
  };
  const currentBackground = riskBackground[riskLevel] ?? riskBackground.low;

  const riskBadgeStyles: Record<string, string> = {
    high: "border-red-200 bg-red-50 text-red-700",
    medium: "border-amber-200 bg-amber-50 text-amber-700",
    low: "border-green-200 bg-green-50 text-green-700",
  };

  const decisionBadgeStyles: Record<string, string> = {
    escalate: "border-red-200 bg-red-50 text-red-700",
    review: "border-amber-200 bg-amber-50 text-amber-700",
    clear: "border-green-200 bg-green-50 text-green-700",
  };

  return (
    <div className={`overflow-hidden rounded-xl ${currentBackground} text-slate-900 shadow-sm`}>
      {/* Top Banner with Risk Level and Decision Badges */}
      <div
        className={`${riskLevel === "high" ? "border-red-200" : riskLevel === "medium" ? "border-amber-200" : "border-emerald-200"} flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 px-6 py-5`}
      >
        <div className="flex items-center gap-4">
          {riskLevel === "high" ? (
            <ShieldAlert size={26} className="shrink-0 text-red-600" />
          ) : riskLevel === "medium" ? (
            <AlertTriangle size={26} className="shrink-0 text-amber-500" />
          ) : (
            <CheckCircle2 size={26} className="shrink-0 text-green-600" />
          )}
          <div>
            <h2 className="text-xl font-bold text-slate-900">
              Tender Risk Assessment
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium text-slate-500">Status</span>
              <span
                className={`inline-block rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                  riskBadgeStyles[riskLevel] || "border-gray-200 bg-slate-100 text-slate-600"
                }`}
              >
                Risk: {fused.risk_level}
              </span>
              <span
                className={`inline-block rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                  decisionBadgeStyles[decision] || "border-gray-200 bg-slate-100 text-slate-600"
                }`}
              >
                Decision: {fused.decision}
              </span>
            </div>
          </div>
        </div>

        {/* Tender ID display */}
        <div className="rounded-lg bg-slate-800 px-3 py-1.5 font-mono text-xs font-medium text-white">
          {fused.tender_id}
        </div>
      </div>

      {/* Card Body */}
      <div className="space-y-5 p-6">
        {/* Summary */}
        {fused.summary && (
          <div className="rounded-lg border border-gray-200 bg-slate-50 p-4 text-sm leading-relaxed text-slate-700">
            {fused.summary}
          </div>
        )}

        {/* Linked Vendors Section */}
        {fused.linked_vendors && fused.linked_vendors.length > 0 && (
          <div className="rounded-lg border border-gray-200 bg-slate-50 p-4">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
              <AlertOctagon
                size={16}
                className={`shrink-0 ${isDanger ? "text-red-600" : "text-amber-600"}`}
              />
              Flagged & Linked Vendors ({fused.linked_vendors.length})
            </h3>
            <div className="divide-y divide-gray-200">
              {fused.linked_vendors.map((vendor, idx) => (
                <div
                  key={`${vendor.vendor_id}-${idx}`}
                  className="flex flex-col justify-between gap-2 py-3 first:pt-1 last:pb-0 sm:flex-row sm:items-center"
                >
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-slate-800 px-2.5 py-1 font-mono text-sm font-medium text-white">
                      {vendor.vendor_id}
                    </span>
                    {vendor.ring_id && (
                      <span
                        className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                          isDanger
                            ? "border-red-200 bg-red-50 text-red-700"
                            : "border-amber-200 bg-amber-50 text-amber-700"
                        }`}
                      >
                        Ring: {vendor.ring_id}
                      </span>
                    )}
                  </div>
                  <div className="rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm text-slate-600 shadow-sm">
                    <span className="font-normal text-slate-500">Reason: </span>
                    <span className={`font-medium ${isDanger ? "text-red-700" : "text-amber-700"}`}>
                      {vendor.reason.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Mandatory Disclaimer (verbatim from FusedData.disclaimer) */}
        {disclaimerText && (
          <p className="mt-4 border-t border-gray-100 pt-4 text-xs text-slate-500">
            {disclaimerText}
          </p>
        )}
      </div>
    </div>
  );
}