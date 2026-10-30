import React from 'react';
import type { FusedData } from "../api/client";
import { ShieldAlert, AlertTriangle, CheckCircle2, Info } from "lucide-react";

interface Props {
  fused: FusedData;
}

const riskConfig: Record<
  string,
  { color: string; bg: string; border: string; icon: React.ReactNode }
> = {
  high: {
    color: "text-red-700",
    bg: "bg-red-50",
    border: "border-red-300",
    icon: <ShieldAlert size={28} className="text-red-600" />,
  },
  medium: {
    color: "text-yellow-700",
    bg: "bg-yellow-50",
    border: "border-yellow-300",
    icon: <AlertTriangle size={28} className="text-yellow-600" />,
  },
  low: {
    color: "text-green-700",
    bg: "bg-green-50",
    border: "border-green-300",
    icon: <CheckCircle2 size={28} className="text-green-600" />,
  },
};

export default function RiskCard({ fused }: Props) {
  const cfg = riskConfig[fused.risk_level] ?? riskConfig["low"];

  return (
    <div className={`rounded-xl border-2 ${cfg.border} ${cfg.bg} p-6`}>
      <div className="flex items-start gap-4">
        <div className="mt-1">{cfg.icon}</div>

        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className={`text-lg font-bold uppercase ${cfg.color}`}>
              Risk: {fused.risk_level}
            </span>
            <span
              className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${fused.decision === "escalate"
                  ? "bg-red-600 text-white"
                  : fused.decision === "review"
                    ? "bg-yellow-500 text-white"
                    : "bg-green-600 text-white"
                }`}
            >
              {fused.decision}
            </span>
          </div>

          <p className="text-sm text-gray-700 mb-3">{fused.summary}</p>

          {fused.linked_vendors.length > 0 && (
            <div className="text-sm mb-3">
              <span className="font-medium text-gray-600">Linked vendors: </span>
              {fused.linked_vendors.map((lv) => (
                <span
                  key={lv.vendor_id}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-red-100 text-red-800 text-xs font-mono mr-1"
                >
                  {lv.vendor_id} ({lv.ring_id})
                </span>
              ))}
            </div>
          )}

          <div className="flex items-start gap-2 mt-3 p-3 bg-white/60 rounded-lg border border-gray-200">
            <Info size={14} className="text-gray-400 mt-0.5 shrink-0" />
            <p className="text-xs text-gray-500 italic">{fused.disclaimer}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

