import { Link, useLocation } from "react-router-dom";
import { KeyRound, LogIn, Gauge, Coins, Snail } from "lucide-react";
import type { LlmCreds } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { isFreeModel, type LlmSettings } from "../auth/llmKey";
import { btnPrimary, link } from "./styles";

export type LlmAction = "regen" | "compile" | "chat";

// Chat stays enabled only while at least this many free-model requests remain: the server may retry a
// turn once when the model cites unknown refs, so one turn can cost two provider requests.
const LOW_FREE_REQUESTS = 2;

export interface LlmGate {
  status: "auth_unavailable" | "signed_out" | "no_key" | "no_model" | "ready";
  mode: "own" | null; // who answers when ready: the user's saved OpenRouter key
  llm: LlmSettings | null;
  model: string | null; // model id to send
  creds: LlmCreds | null;
  isFree: boolean;
  ourRemaining: number | null; // our per-user daily counter for this action
  freeRemaining: number | null; // OpenRouter free_model_daily_requests.remaining at the last key check
  low: boolean;
}

export function useLlmGate(action: LlmAction): LlmGate {
  const { configured, signedIn, me, llm } = useAuth();
  const isFree = isFreeModel(llm);
  const ourRemaining = me ? Math.max(0, me.limits[action] - me.usage[action]) : null;
  const fmdr = llm?.detect?.key_info?.free_model_daily_requests;
  const freeRemaining = isFree && fmdr ? fmdr.remaining : null;
  const exhausted = ourRemaining !== null && ourRemaining <= 0;
  const freeLow =
    freeRemaining !== null && freeRemaining < (action === "chat" ? LOW_FREE_REQUESTS : 1);
  const mode: LlmGate["mode"] = !signedIn || !llm ? null : "own";
  const status: LlmGate["status"] = !signedIn
    ? configured
      ? "signed_out"
      : "auth_unavailable"
    : !llm
      ? "no_key"
      : !llm.model
        ? "no_model"
        : "ready";
  const model = llm?.model ?? null;
  const creds = llm ? { key: llm.key, provider: llm.provider ?? undefined } : null;
  return { status, mode, llm, model, creds, isFree, ourRemaining, freeRemaining, low: exhausted || freeLow };
}

// Prompt shown instead of a generation control when the user cannot use it yet.
export function GatePrompt({ gate, verb }: { gate: LlmGate; verb: string }) {
  const { login } = useAuth();
  const location = useLocation();
  if (gate.status === "auth_unavailable") {
    return (
      <p className="text-sm font-bold text-gray-800" data-testid="gate-auth-unavailable">
        Sign-in is not configured on this server, so {verb} is unavailable. The demo stays fully browsable.
      </p>
    );
  }
  if (gate.status === "signed_out") {
    return (
      <div className="flex flex-wrap items-center gap-3" data-testid="gate-signed-out">
        <p className="text-sm font-bold text-gray-900">Sign in to {verb}. Browsing the demo needs no account.</p>
        <button type="button" className={btnPrimary} onClick={() => void login(location.pathname)}>
          <LogIn size={16} /> Sign in
        </button>
      </div>
    );
  }
  if (gate.status === "no_key" || gate.status === "no_model") {
    return (
      <div className="flex flex-wrap items-center gap-3" data-testid="gate-no-key">
        <p className="text-sm font-bold text-gray-900">
          {gate.status === "no_key"
            ? "Add your OpenRouter key in Settings to use this."
            : `Pick a model for your key to ${verb}.`}
        </p>
        <Link to="/settings/ai" className={btnPrimary}>
          <KeyRound size={16} /> Settings
        </Link>
      </div>
    );
  }
  return null;
}

// Who answers and what it costs: site AI's shared monthly budget, or the user's free/paid key.
export function BudgetNote({ gate, action }: { gate: LlmGate; action: LlmAction }) {
  if (gate.status !== "ready") return null;
  const actionLabel = { regen: "re-generations", compile: "compiles", chat: "chat messages" }[action];
  const ours = gate.ourRemaining !== null && (
    <span className="inline-flex items-center gap-1">
      <Gauge size={14} /> {gate.ourRemaining} {actionLabel} left today on TenderFender
    </span>
  );
  if (!gate.llm) return null;
  return (
    <div
      data-testid="budget-note"
      className={`flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-bold px-3 py-2 rounded-lg border-2 ${
        gate.isFree ? "bg-amber-50 border-amber-600 text-amber-950" : "bg-blue-50 border-blue-800 text-blue-950"
      }`}
    >
      <span className="font-mono">
        {gate.llm.provider ?? "provider"} · {gate.llm.model}
      </span>
      {gate.isFree ? (
        <span className="inline-flex items-center gap-1">
          <Snail size={14} /> Free model: slow, may be rate-limited.
        </span>
      ) : (
        <span className="inline-flex items-center gap-1">
          <Coins size={14} /> Billed to your provider account.
        </span>
      )}
      {ours}
      {gate.freeRemaining !== null && (
        <span>
          {gate.freeRemaining} free-model requests left today per OpenRouter (at last{" "}
          <Link to="/settings/ai" className={link}>
            key check
          </Link>
          )
        </span>
      )}
    </div>
  );
}
