import { useState } from "react";
import type { RulesData, Clause, Finding } from "../api/client";
import { CheckCircle, Circle, AlertTriangle } from "lucide-react";

interface Props {
  rules: RulesData;
  clauses: Clause[];
  onConfirm: (atomId: string) => void;
}

export default function ClausePanel({ rules, onConfirm }: Props) {
  const [confirming, setConfirming] = useState<string | null>(null);

  // Collect clause IDs that appear in findings (bad clauses)
  const flaggedClauseIds = new Set<string>();
  for (const f of rules.findings) {
    for (const cid of f.clause_ids) {
      flaggedClauseIds.add(cid);
    }
  }

  const handleConfirm = async (atomId: string) => {
    setConfirming(atomId);
    try {
      await onConfirm(atomId);
    } finally {
      setConfirming(null);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        Clauses & Formalization
      </h2>

      {/* Status badge */}
      <div className="mb-4">
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${rules.formalization_status === "confirmed"
              ? "bg-green-100 text-green-700"
              : "bg-yellow-100 text-yellow-700"
            }`}
        >
          {rules.formalization_status === "confirmed" ? (
            <CheckCircle size={12} />
          ) : (
            <Circle size={12} />
          )}
          Formalization: {rules.formalization_status}
        </span>
      </div>

      {/* Findings */}
      {rules.findings.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Findings</h3>
          {rules.findings.map((f: Finding) => (
            <div
              key={f.finding_id}
              className="p-3 mb-2 rounded-lg border border-red-200 bg-red-50"
            >
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle size={14} className="text-red-600" />
                <span className="text-sm font-semibold text-red-800">
                  {f.finding_id}: {f.type.replace("_", " ")}
                </span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-red-200 text-red-800 uppercase">
                  {f.severity}
                </span>
              </div>
              <p className="text-xs text-gray-700">{f.explanation}</p>
              <p className="text-xs text-gray-500 mt-1 font-mono">
                Proof: {f.proof.detail}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Clauses */}
      <h3 className="text-sm font-medium text-gray-600 mb-2">
        Formalized Atoms
      </h3>
      <div className="space-y-2">
        {rules.atoms.map((atom) => {
          const isFlagged = flaggedClauseIds.has(atom.clause_id);
          return (
            <div
              key={atom.id}
              className={`p-3 rounded-lg border ${isFlagged
                  ? "border-red-300 bg-red-50"
                  : "border-gray-200 bg-gray-50"
                }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs font-semibold text-gray-600">
                      {atom.id}
                    </span>
                    <span className="text-xs text-gray-400">
                      ({atom.clause_id})
                    </span>
                    {isFlagged && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-red-200 text-red-700">
                        flagged
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-700">{atom.source_text}</p>
                  <p className="text-xs text-gray-400 font-mono mt-1">
                    {atom.field} {atom.op}{" "}
                    {Array.isArray(atom.value)
                      ? atom.value.join(", ")
                      : String(atom.value)}
                  </p>
                </div>
                <button
                  onClick={() => handleConfirm(atom.id)}
                  disabled={
                    confirming === atom.id ||
                    rules.formalization_status === "confirmed"
                  }
                  className={`shrink-0 p-1.5 rounded-lg transition-colors ${rules.formalization_status === "confirmed"
                      ? "text-green-600 bg-green-100"
                      : "text-gray-400 hover:text-green-600 hover:bg-green-50"
                    }`}
                  title="Confirm formalization"
                >
                  {rules.formalization_status === "confirmed" ? (
                    <CheckCircle size={18} />
                  ) : (
                    <Circle size={18} />
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Qualifying vendors */}
      {rules.qualifying_vendors.length > 0 && (
        <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <span className="text-xs font-medium text-blue-700">
            Qualifying vendors ({rules.qualifying_vendors.length} /{" "}
            {rules.vendors_evaluated}):
          </span>
          <span className="text-xs text-blue-600 font-mono ml-2">
            {rules.qualifying_vendors.join(", ")}
          </span>
        </div>
      )}
    </div>
  );
}

