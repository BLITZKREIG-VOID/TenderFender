import { useState } from "react";
import type { RulesData, Clause, Finding } from "../api/client";
import { CheckCircle2, Circle, AlertTriangle, ShieldCheck, Scale } from "lucide-react";

interface Props {
  rules: RulesData;
  clauses?: Clause[];
  onConfirm: (atomId: string) => Promise<void> | void;
  /** Red accents are reserved for high-risk or escalate tenders. */
  isDanger?: boolean;
}

export default function ClausePanel({ rules, onConfirm, isDanger = false }: Props) {
  const [optimisticStatuses, setOptimisticStatuses] = useState<Record<string, string>>({});
  const [cooldown, setCooldown] = useState(false);

  // Collect clause IDs that appear in findings (bad clauses)
  const flaggedClauseIds = new Set<string>();
  for (const f of rules.findings) {
    for (const cid of f.clause_ids) {
      flaggedClauseIds.add(cid);
    }
  }

  const handleConfirm = async (atomId: string) => {
    if (cooldown) return;

    // Optimistic rendering: show confirmation instantly.
    setOptimisticStatuses((prev) => ({ ...prev, [atomId]: "confirmed" }));
    setCooldown(true);

    try {
      await onConfirm(atomId);
    } catch {
      // Off the happy path: revert if the server rejects the confirmation.
      setOptimisticStatuses((prev) => {
        const next = { ...prev };
        delete next[atomId];
        return next;
      });
    } finally {
      // Throttle rapid clicks for one second.
      setTimeout(() => setCooldown(false), 1000);
    }
  };

  const isConfirmed = rules.formalization_status === "confirmed";

  return (
    <div className="flex flex-col justify-between rounded-xl border border-gray-200 bg-white p-6 text-slate-900 shadow-sm">
      <div>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 pb-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-800">
            <Scale size={20} className="text-slate-500" />
            Clause Formalization & Logic Proofs
          </h2>

          {/* Formalization Status Badge */}
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
              isConfirmed
                ? "border-green-200 bg-green-50 text-green-700"
                : "border-amber-200 bg-amber-50 text-amber-700"
            }`}
          >
            {isConfirmed ? (
              <ShieldCheck size={14} strokeWidth={2} />
            ) : (
              <Circle size={12} strokeWidth={2} />
            )}
            Status: {rules.formalization_status}
          </span>
        </div>

        {/* Solver Findings Section */}
        {rules.findings.length > 0 ? (
          <div className="mb-6 space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
              <AlertTriangle
                size={16}
                className={isDanger ? "text-red-600" : "text-amber-600"}
              />
              Automated Solver Findings ({rules.findings.length})
            </h3>
            {rules.findings.map((f: Finding) => (
              <div
                key={f.finding_id}
                className={`rounded-lg border p-4 ${
                  isDanger
                    ? "border-red-200 bg-red-50"
                    : "border-amber-200 bg-amber-50"
                }`}
              >
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-slate-800 px-2 py-0.5 font-mono text-xs font-medium text-white">
                      {f.finding_id}
                    </span>
                    <span className="text-sm font-semibold text-slate-800">
                      {f.type.replace(/_/g, " ")}
                    </span>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-white ${
                      isDanger ? "bg-red-600" : "bg-amber-600"
                    }`}
                  >
                    Severity: {f.severity}
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-slate-700">
                  {f.explanation}
                </p>
                <div className="mt-3 rounded-md border border-gray-200 bg-white/80 p-3 font-mono text-xs text-slate-700">
                  <span className={isDanger ? "text-red-700" : "text-amber-700"}>
                    Formal Proof:
                  </span>{" "}
                  {f.proof.detail}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mb-6 flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 p-4 text-green-800">
            <CheckCircle2 size={22} className="shrink-0 text-green-600" />
            <div>
              <p className="text-sm font-semibold">Z3 Solver Verification: Clean</p>
              <p className="text-xs text-green-700">
                No formal contradictions or artificial exclusivity criteria detected.
              </p>
            </div>
          </div>
        )}

        {/* Formalized Atoms List */}
        <div>
          <h3 className="mb-3 text-sm font-semibold text-slate-700">
            Formalized Tender Criteria (Atoms)
          </h3>
          <div className="space-y-3">
            {rules.atoms.map((atom) => {
              const isFlagged = flaggedClauseIds.has(atom.clause_id);
              const atomStatus =
                optimisticStatuses[atom.id] ??
                atom.formalization_status ??
                rules.formalization_status;
              const isAtomConfirmed = atomStatus === "confirmed";

              return (
                <div
                  key={atom.id}
                  className={`rounded-lg border p-4 transition-colors ${
                    isFlagged
                      ? isDanger
                        ? "border-red-200 bg-red-50/70"
                        : "border-amber-200 bg-amber-50/70"
                      : "border-gray-200 bg-slate-50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className="rounded-md bg-slate-800 px-2 py-0.5 font-mono text-xs font-medium text-white">
                          {atom.id}
                        </span>
                        <span className="rounded-md border border-gray-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-600">
                          Clause: {atom.clause_id}
                        </span>
                        {isFlagged && (
                          <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                              isDanger
                                ? "border-red-200 bg-red-50 text-red-700"
                                : "border-amber-200 bg-amber-50 text-amber-700"
                            }`}
                          >
                            Flagged in core
                          </span>
                        )}
                      </div>
                      <p className="text-sm leading-relaxed text-slate-700">
                        "{atom.source_text}"
                      </p>
                      <div className="mt-2 inline-block rounded-md border border-blue-100 bg-blue-50 px-2.5 py-1 font-mono text-xs text-blue-700">
                        IR Formula: {atom.field} {atom.op}{" "}
                        {Array.isArray(atom.value)
                          ? `[${atom.value.join(", ")}]`
                          : String(atom.value)}
                      </div>
                    </div>

                    {/* Action Button: Confirm Clause */}
                    <button
                      onClick={() => handleConfirm(atom.id)}
                      disabled={cooldown || isAtomConfirmed}
                      aria-label={
                        isAtomConfirmed
                          ? `Clause ${atom.id} confirmed`
                          : `Confirm clause for atom ${atom.id}`
                      }
                      title={
                        isAtomConfirmed ? "Clause Confirmed" : "Confirm Clause"
                      }
                      className={`shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-hidden focus:ring-2 focus:ring-blue-500 ${
                        isAtomConfirmed
                          ? "cursor-not-allowed bg-slate-100 text-slate-400"
                          : cooldown
                            ? "cursor-not-allowed bg-slate-500 text-white"
                            : "cursor-pointer bg-slate-800 text-white hover:bg-slate-700"
                      } disabled:opacity-80`}
                    >
                      {isAtomConfirmed ? "Clause Confirmed" : "Confirm Clause"}
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
        <div className="mt-6 rounded-lg border border-gray-200 bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-medium text-slate-600">
              Eligible Bidders Passing Criteria:
            </span>
            <span className="rounded-md border border-gray-200 bg-white px-2 py-0.5 font-mono text-xs text-slate-600">
              {rules.qualifying_vendors.length} of {rules.vendors_evaluated} vendors evaluated
            </span>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {rules.qualifying_vendors.map((vid) => (
              <span
                key={vid}
                className="rounded-md bg-slate-800 px-2 py-1 font-mono text-xs font-medium text-white"
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
