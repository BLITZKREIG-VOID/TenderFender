import { useState } from "react";
import type { RulesData, Clause, Finding } from "../api/client";
import { CheckCircle2, Circle, AlertTriangle, ShieldCheck, Scale, Check } from "lucide-react";

interface Props {
  rules: RulesData;
  clauses?: Clause[];
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

  const isConfirmed = rules.formalization_status === "confirmed";

  return (
    <div className="bg-white rounded-xl shadow-md border-4 border-gray-900 p-6 text-black flex flex-col justify-between">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-gray-300 pb-3 mb-5">
          <h2 className="text-xl font-black text-black flex items-center gap-2 uppercase tracking-wide">
            <Scale size={24} className="text-black" />
            Clause Formalization & Logic Proofs
          </h2>

          {/* Formalization Status Badge */}
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs sm:text-sm font-black uppercase tracking-wider border-2 shadow-2xs ${
              isConfirmed
                ? "bg-green-700 text-white border-green-950"
                : "bg-orange-600 text-white border-orange-950"
            }`}
          >
            {isConfirmed ? (
              <ShieldCheck size={16} strokeWidth={2.5} />
            ) : (
              <Circle size={14} strokeWidth={2.5} />
            )}
            Status: {rules.formalization_status}
          </span>
        </div>

        {/* Solver Findings Section */}
        {rules.findings.length > 0 ? (
          <div className="mb-6 space-y-3">
            <h3 className="text-xs font-black text-black uppercase tracking-wider flex items-center gap-1.5">
              <AlertTriangle size={16} className="text-red-700" />
              Automated Solver Findings ({rules.findings.length})
            </h3>
            {rules.findings.map((f: Finding) => (
              <div
                key={f.finding_id}
                className="p-4 rounded-lg border-2 border-red-700 bg-red-50 text-black shadow-2xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-black px-2 py-0.5 rounded bg-black text-white">
                      {f.finding_id}
                    </span>
                    <span className="text-sm font-black text-red-950 uppercase tracking-tight">
                      {f.type.replace(/_/g, " ")}
                    </span>
                  </div>
                  <span className="text-xs font-black px-2.5 py-0.5 rounded bg-red-700 text-white border border-red-950 uppercase tracking-wider">
                    Severity: {f.severity}
                  </span>
                </div>
                <p className="text-sm sm:text-base font-bold text-gray-950 leading-snug">
                  {f.explanation}
                </p>
                <div className="mt-2.5 p-2 bg-white/90 rounded border border-red-300 text-xs font-mono font-bold text-gray-900">
                  <span className="text-red-800">Formal Proof:</span> {f.proof.detail}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mb-6 p-4 bg-green-50 rounded-lg border-2 border-green-700 text-green-950 flex items-center gap-3">
            <CheckCircle2 size={24} className="text-green-700 shrink-0" />
            <div>
              <p className="text-sm font-black uppercase">Z3 Solver Verification: CLEAN</p>
              <p className="text-xs font-bold text-green-900">
                No formal contradictions or artificial exclusivity criteria detected.
              </p>
            </div>
          </div>
        )}

        {/* Formalized Atoms List */}
        <div>
          <h3 className="text-xs font-black text-black uppercase tracking-wider mb-3">
            Formalized Tender Criteria (Atoms)
          </h3>
          <div className="space-y-3">
            {rules.atoms.map((atom) => {
              const isFlagged = flaggedClauseIds.has(atom.clause_id);
              const isThisConfirming = confirming === atom.id;

              return (
                <div
                  key={atom.id}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    isFlagged
                      ? "border-red-600 bg-red-50/70"
                      : "border-gray-300 bg-gray-50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                        <span className="font-mono text-xs font-black px-2 py-0.5 rounded bg-gray-900 text-white">
                          {atom.id}
                        </span>
                        <span className="text-xs font-bold text-gray-800 bg-white px-2 py-0.5 rounded border border-gray-400">
                          Clause: {atom.clause_id}
                        </span>
                        {isFlagged && (
                          <span className="text-xs font-black px-2 py-0.5 rounded bg-red-700 text-white border border-red-950 uppercase tracking-wider">
                            Flagged in core
                          </span>
                        )}
                      </div>
                      <p className="text-sm sm:text-base font-bold text-gray-950 leading-snug">
                        "{atom.source_text}"
                      </p>
                      <div className="mt-2 font-mono text-xs font-black text-blue-900 bg-blue-50 px-2.5 py-1 rounded inline-block border border-blue-200">
                        IR Formula: {atom.field} {atom.op}{" "}
                        {Array.isArray(atom.value)
                          ? `[${atom.value.join(", ")}]`
                          : String(atom.value)}
                      </div>
                    </div>

                    {/* Action Button: Confirm Formalization */}
                    <button
                      onClick={() => handleConfirm(atom.id)}
                      disabled={isThisConfirming || isConfirmed}
                      aria-label={
                        isConfirmed
                          ? "Formalization confirmed by auditor"
                          : `Confirm formalization translation for atom ${atom.id}`
                      }
                      title={
                        isConfirmed
                          ? "Formalization Confirmed"
                          : "Click to Confirm Formalization"
                      }
                      className={`shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-lg font-black text-xs uppercase tracking-wider border-2 shadow-2xs transition-all focus:outline-hidden focus:ring-4 focus:ring-blue-600 cursor-pointer ${
                        isConfirmed
                          ? "bg-green-700 text-white border-green-950 cursor-default"
                          : "bg-black hover:bg-gray-800 text-white border-black"
                      } disabled:opacity-80`}
                    >
                      {isConfirmed ? (
                        <>
                          <Check size={16} strokeWidth={3} />
                          <span className="hidden sm:inline">Verified</span>
                        </>
                      ) : isThisConfirming ? (
                        <span>Saving...</span>
                      ) : (
                        <>
                          <CheckCircle2 size={16} />
                          <span className="hidden sm:inline">Confirm</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Qualifying Vendors Summary Footer */}
      {rules.qualifying_vendors.length > 0 && (
        <div className="mt-6 p-4 bg-gray-100 rounded-lg border-2 border-black">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="text-xs font-black uppercase text-black tracking-wide">
              Eligible Bidders Passing Criteria:
            </span>
            <span className="text-xs font-mono font-bold bg-white px-2 py-0.5 rounded border border-black">
              {rules.qualifying_vendors.length} of {rules.vendors_evaluated} vendors evaluated
            </span>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {rules.qualifying_vendors.map((vid) => (
              <span
                key={vid}
                className="font-mono text-xs font-black px-2 py-1 bg-black text-white rounded border border-black"
              >
                {vid}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
