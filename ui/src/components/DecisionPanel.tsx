import type { FusedData } from "../api/client";
import { FileText, Lightbulb, Quote } from "lucide-react";

interface Props {
  fused: FusedData;
}

const citationStyle: Record<string, string> = {
  guideline: "bg-blue-100 text-blue-800",
  finding: "bg-red-100 text-red-800",
  ring: "bg-purple-100 text-purple-800",
};

export default function DecisionPanel({ fused }: Props) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <FileText size={20} /> Decision & Reasoning
      </h2>

      {/* Reasoning */}
      <div className="mb-4">
        <h3 className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-1">
          <Lightbulb size={14} /> Reasoning
        </h3>
        <p className="text-sm text-gray-700 leading-relaxed bg-gray-50 p-4 rounded-lg border border-gray-100">
          {fused.reasoning}
        </p>
      </div>

      {/* Citations */}
      {fused.citations.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-1">
            <Quote size={14} /> Citations
          </h3>
          <div className="flex flex-wrap gap-2">
            {fused.citations.map((cite, i) => (
              <span
                key={i}
                className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-mono font-medium cursor-pointer hover:opacity-80 transition-opacity ${citationStyle[cite.kind] ?? "bg-gray-100 text-gray-800"
                  }`}
                title={`${cite.kind}: ${cite.ref}`}
              >
                {cite.ref}
                <span className="text-[10px] opacity-60">({cite.kind})</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Recommended actions */}
      {fused.recommended_actions.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-gray-600 mb-2">
            Recommended Actions
          </h3>
          <ol className="list-decimal list-inside space-y-1">
            {fused.recommended_actions.map((action, i) => (
              <li key={i} className="text-sm text-gray-700">
                {action}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Source badge */}
      <div className="text-xs text-gray-400">
        Decision source:{" "}
        <span className="font-mono">{fused.decision_source}</span>
      </div>
    </div>
  );
}

