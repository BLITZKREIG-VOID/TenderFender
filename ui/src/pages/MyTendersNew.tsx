import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { FileUp, Loader2, CheckCircle2, ArrowLeft } from "lucide-react";
import { api, apiError, describeError, type CompileResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { isFreeOpenRouterKey } from "../auth/llmKey";
import CaseFile from "../components/CaseFile";
import { useLlmGate, GatePrompt, BudgetNote } from "../components/LlmGate";
import ModelSelect from "../components/ModelSelect";
import { btnPrimary, btnSecondary, input, label, errorBox, link } from "../components/styles";

const MAX_TEXT_LEN = 20000;

export default function MyTendersNew() {
  const { refreshMe } = useAuth();
  const gate = useLlmGate("compile");

  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [model, setModel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CompileResponse | null>(null);

  const chosenModel = model ?? gate.llm?.model ?? null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !text.trim() || !chosenModel || !gate.llm || busy) return;

    setBusy(true);
    setError(null);
    try {
      const res = await api.compile(
        {
          title: title.trim(),
          text: text.trim(),
          model: chosenModel,
        },
        { key: gate.llm.key, provider: gate.llm.provider ?? undefined }
      );
      setResult(res.data);
      void refreshMe();
    } catch (err) {
      setError(describeError(apiError(err, "Compilation failed")));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="my-tenders-new-page">
      <div className="flex items-center gap-2 mb-2">
        <Link to="/my-tenders" className={`inline-flex items-center gap-1 text-sm ${link}`}>
          <ArrowLeft size={16} /> Back to My Tenders
        </Link>
      </div>

      <CaseFile
        testId="compile-case-file"
        fileNo="COMPILE/BETA/2026-27"
        title="Compile Tender Eligibility Document"
        icon={<FileUp size={24} />}
        stampLabel="Beta feature: compile is still in development"
        status="Bids under technical evaluation — this assistant has not yet been awarded the contract."
        caveat="Our investigator is still gathering evidence. Answers may be wrong; verify against the cited clauses and passages."
      >
        {gate.status !== "ready" ? (
          <GatePrompt gate={gate} verb="compile and analyze custom tender text" />
        ) : (
          <div className="space-y-6">
            <BudgetNote gate={gate} action="compile" />

            {result ? (
              <div className="space-y-6" data-testid="compile-result">
                <div className="p-4 bg-emerald-50 border-2 border-emerald-700 rounded-lg">
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="flex items-center gap-2 font-black text-emerald-950 text-base">
                      <CheckCircle2 size={20} className="text-emerald-700" /> Tender Compiled Successfully
                    </span>
                    <span className="font-mono text-xs font-black px-2.5 py-1 bg-black text-white rounded">
                      {result.tender_id}
                    </span>
                  </div>
                  <p className="text-xs font-bold text-emerald-900">
                    Extracted {result.clauses?.length ?? 0} clauses, {result.atoms?.length ?? 0} requirement atoms, and{" "}
                    {result.findings?.length ?? 0} risk indicators.
                  </p>
                </div>

                {/* Findings summary */}
                <div>
                  <h3 className="text-sm font-black uppercase tracking-wider text-black mb-2">
                    Risk Indicators ({result.findings?.length ?? 0})
                  </h3>
                  {result.findings && result.findings.length > 0 ? (
                    <div className="space-y-2">
                      {result.findings.map((f, i) => (
                        <div key={i} className="p-3 bg-amber-50 border-2 border-amber-700 rounded-lg text-sm">
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className="font-mono text-xs font-black uppercase px-2 py-0.5 bg-amber-200 text-amber-950 rounded">
                              {f.type}
                            </span>
                            <span className="text-xs font-bold text-gray-700">{f.severity}</span>
                          </div>
                          <p className="font-bold text-gray-950">{f.explanation}</p>
                          {f.clause_ids && f.clause_ids.length > 0 && (
                            <span className="text-xs font-mono font-bold text-gray-700 mt-1 block">
                              Clause Refs: {f.clause_ids.join(", ")}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm font-bold text-emerald-800 p-3 bg-emerald-50 border-2 border-emerald-500 rounded">
                      No rule contradictions or risk indicators detected in this text.
                    </p>
                  )}
                </div>

                {/* Vendor check note */}
                {result.vendor_check && (
                  <div className="p-3 bg-gray-100 border border-gray-400 rounded text-xs font-semibold text-gray-800">
                    <strong>Vendor check:</strong> {result.vendor_check.status} ({result.vendor_check.reason})
                  </div>
                )}

                <div className="flex items-center gap-3 pt-2">
                  <Link to="/my-tenders" className={btnPrimary}>
                    View in My Tenders
                  </Link>
                  <button
                    type="button"
                    className={btnSecondary}
                    onClick={() => {
                      setResult(null);
                      setTitle("");
                      setText("");
                    }}
                  >
                    Compile another tender
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
                <div>
                  <label htmlFor="tender-title" className={label}>
                    Tender Title / Identification
                  </label>
                  <input
                    id="tender-title"
                    type="text"
                    className={input}
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Supply and Installation of Cryogenic Storage Tanks"
                    required
                    disabled={busy}
                    data-testid="tender-title-input"
                  />
                </div>

                {gate.llm?.detect && (
                  <ModelSelect
                    id="compile-model"
                    models={gate.llm.detect.models}
                    value={chosenModel}
                    onChange={setModel}
                    freeFirst={isFreeOpenRouterKey(gate.llm.detect)}
                    recommended={gate.llm.detect.recommended_model}
                  />
                )}

                <div>
                  <div className="flex justify-between items-center mb-1.5">
                    <label htmlFor="tender-text" className={label}>
                      Eligibility & Technical Requirements Text
                    </label>
                    <span className="text-xs font-bold text-gray-600 font-mono">
                      {text.length} / {MAX_TEXT_LEN} chars
                    </span>
                  </div>
                  <textarea
                    id="tender-text"
                    className={`${input} min-h-60 font-mono text-sm`}
                    value={text}
                    maxLength={MAX_TEXT_LEN}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Paste the eligibility criteria, qualification clauses, and turnover requirements from the tender document…"
                    required
                    disabled={busy}
                    data-testid="tender-text-input"
                  />
                  <p className="text-xs font-bold text-gray-600 mt-1">
                    Accepts up to 20,000 characters. TenderFender splits clauses, extracts logic atoms, and checks for contradictions and mismatch risks.
                  </p>
                </div>

                {error && (
                  <div role="alert" className={errorBox}>
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  className={btnPrimary}
                  disabled={busy || !title.trim() || !text.trim() || !chosenModel || gate.low}
                  data-testid="compile-tender-btn"
                >
                  {busy ? (
                    <>
                      <Loader2 size={16} className="animate-spin" /> Compiling clauses and evaluating rules…
                    </>
                  ) : (
                    "Compile & check tender"
                  )}
                </button>
              </form>
            )}
          </div>
        )}
      </CaseFile>
    </div>
  );
}
