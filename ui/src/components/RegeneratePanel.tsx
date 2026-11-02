import { useState } from "react";
import { Sparkles, Loader2 } from "lucide-react";
import { api, apiError, describeError, type RegenerateResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { isFreeOpenRouterKey } from "../auth/llmKey";
import { useLlmGate, GatePrompt, BudgetNote } from "./LlmGate";
import ModelSelect from "./ModelSelect";
import { btnPrimary, btnSecondary, errorBox, panel } from "./styles";

interface Props {
  tenderId: string;
  result: RegenerateResponse | null;
  showing: "shared" | "user";
  onResult: (r: RegenerateResponse) => void;
  onShow: (which: "shared" | "user") => void;
}

// "Re-generate with AI": site AI or the user's key rewrites reasoning/actions/citations; risk level and decision stay fixed.
export default function RegeneratePanel({ tenderId, result, showing, onResult, onShow }: Props) {
  const { refreshMe } = useAuth();
  const gate = useLlmGate("regen");
  const [model, setModel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chosen = model ?? gate.model;

  const run = async () => {
    if (gate.status !== "ready" || !chosen) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.regenerate(tenderId, chosen, gate.creds);
      onResult(r.data);
      onShow("user");
    } catch (err) {
      setError(describeError(apiError(err, "Re-generation failed")));
    } finally {
      setBusy(false);
      void refreshMe();
    }
  };

  return (
    <div className={panel} data-testid="regenerate-panel">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-gray-300 pb-3 mb-4">
        <h2 className="text-xl font-black text-black flex items-center gap-2 uppercase tracking-wide">
          <Sparkles size={24} /> Re-generate with AI
        </h2>
        {result && (
          <div role="group" aria-label="Choose which reasoning to show" className="flex gap-2">
            {(["shared", "user"] as const).map((w) => (
              <button
                key={w}
                type="button"
                aria-pressed={showing === w}
                onClick={() => onShow(w)}
                className={`px-3 py-1.5 rounded-md text-xs font-black uppercase tracking-wider border-2 border-black cursor-pointer focus:outline-hidden focus:ring-4 focus:ring-blue-600 ${
                  showing === w ? "bg-black text-white" : "bg-white text-black hover:bg-gray-100"
                }`}
              >
                {w === "shared" ? "Shared analysis" : "My result"}
              </button>
            ))}
          </div>
        )}
      </div>
      <p className="text-sm font-semibold text-gray-900 mb-4">
        The model rewrites the reasoning, recommended actions and citations from the same evidence. The risk level and
        decision stay fixed, every citation is checked by the validator, and the shared analysis is never overwritten.
      </p>

      {gate.status !== "ready" ? (
        <GatePrompt gate={gate} verb="re-generate the reasoning" />
      ) : (
        <div className="space-y-3">
          <BudgetNote gate={gate} action="regen" />
          <div className="flex flex-wrap items-end gap-3">
            {gate.mode === "own" && (
              <ModelSelect
                id="regen-model"
                models={gate.llm?.detect?.models ?? []}
                value={chosen}
                onChange={setModel}
                freeFirst={isFreeOpenRouterKey(gate.llm?.detect)}
                recommended={gate.llm?.detect?.recommended_model}
              />
            )}
            <button
              type="button"
              className={btnPrimary}
              onClick={() => void run()}
              disabled={busy || gate.low || !chosen}
              data-testid="regenerate-button"
            >
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
              {busy ? "Generating…" : "Re-generate"}
            </button>
            {result && showing === "shared" && (
              <button type="button" className={btnSecondary} onClick={() => onShow("user")}>
                Show my result
              </button>
            )}
          </div>
          {busy && (
            <p role="status" className="text-sm font-bold text-gray-800">
              Waiting for the model{gate.isFree ? "; free models can be slow" : ""}…
            </p>
          )}
          {gate.low && !busy && (
            <p className="text-sm font-bold text-red-900">No re-generations left today for this key or account.</p>
          )}
        </div>
      )}

      {error && (
        <div role="alert" className={`${errorBox} mt-4`}>
          {error}
        </div>
      )}
      {result && (
        <p className="mt-4 text-xs font-mono font-bold text-gray-800" data-testid="regen-meta">
          Last re-generation: {result.provider} · {result.model}
          {result.validated ? " · citations validated" : ""}
          {result.retrieval ? ` · passages: ${result.retrieval}` : ""}
        </p>
      )}
    </div>
  );
}
