import { useState } from "react";
import { Link } from "react-router-dom";
import { KeyRound, ShieldAlert, CheckCircle2, AlertTriangle, HelpCircle, Loader2, Save, Trash2 } from "lucide-react";
import { api, apiError, describeError, type DetectResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { maskKey, isFreeOpenRouterKey, type LlmSettings } from "../auth/llmKey";
import ModelSelect from "../components/ModelSelect";
import {
  panel,
  btnPrimary,
  btnDanger,
  input,
  label,
  errorBox,
  noteBox,
  link,
} from "../components/styles";

export default function SettingsAi() {
  const { signedIn, llm, setLlm } = useAuth();
  const [keyInput, setKeyInput] = useState(llm?.key ?? "");
  const [remember, setRemember] = useState(llm?.remember ?? false);
  const [detectResult, setDetectResult] = useState<DetectResponse | null>(llm?.detect ?? null);
  const [selectedModel, setSelectedModel] = useState<string | null>(llm?.model ?? null);
  const [providerHint, setProviderHint] = useState<string | null>(llm?.provider ?? null);
  const [hintRequired, setHintRequired] = useState(false);
  const [hintCandidates, setHintCandidates] = useState<string[]>(["openai", "deepseek"]);
  const [selectedHint, setSelectedHint] = useState<string>("openai");
  const [detecting, setDetecting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleDetect = async (overrideHint?: string) => {
    const trimmed = keyInput.trim();
    if (!trimmed) {
      setError("Please paste an API key to detect.");
      return;
    }
    setDetecting(true);
    setError(null);
    setSavedSuccess(false);

    const hintToSend = overrideHint ?? (hintRequired ? selectedHint : providerHint ?? undefined);

    try {
      const res = await api.detectKey({ key: trimmed, provider: hintToSend });
      setDetectResult(res.data);
      setHintRequired(false);
      const chosenProvider = res.data.provider || hintToSend || null;
      setProviderHint(chosenProvider);
      if (!res.data.valid) {
        setError("The provided API key was rejected by the provider or unrecognized.");
      } else {
        const rec = res.data.recommended_model;
        const first = res.data.models[0]?.id ?? null;
        setSelectedModel(rec ?? first);
      }
    } catch (err) {
      const errInfo = apiError(err, "Failed to validate API key with server.");
      if (errInfo.code === "provider_hint_required" || (errInfo.status === 400 && errInfo.code === "provider_hint_required")) {
        setHintRequired(true);
        const candidates = errInfo.candidates && errInfo.candidates.length > 0
          ? errInfo.candidates
          : ["openai", "deepseek"];
        setHintCandidates(candidates);
        if (!selectedHint || !candidates.includes(selectedHint)) {
          setSelectedHint(candidates[0]);
        }
        setError("This key format is ambiguous between multiple providers. Please select your provider below to continue.");
        setDetectResult(null);
      } else {
        setError(describeError(errInfo));
        setDetectResult(null);
      }
    } finally {
      setDetecting(false);
    }
  };

  const handleSave = () => {
    if (!detectResult || !detectResult.valid || !selectedModel) {
      setError("Please detect a valid key and select a model before saving.");
      return;
    }
    setSaving(true);
    const resolvedProvider = detectResult.provider || providerHint;
    const settings: LlmSettings = {
      key: keyInput.trim(),
      provider: resolvedProvider,
      model: selectedModel,
      remember,
      detect: detectResult,
      checked_at: new Date().toISOString(),
    };
    setLlm(settings);
    setSaving(false);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 4000);
  };

  const handleClear = () => {
    setLlm(null);
    setKeyInput("");
    setDetectResult(null);
    setSelectedModel(null);
    setProviderHint(null);
    setHintRequired(false);
    setRemember(false);
    setError(null);
  };
  const isFree = isFreeOpenRouterKey(detectResult);

  return (
    <div className={`max-w-3xl mx-auto space-y-6`} data-testid="settings-ai-page">
      <div className={panel}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-gray-300 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="p-1.5 bg-black rounded-md text-white">
              <KeyRound size={22} />
            </span>
            <h1 className="text-xl font-black text-black uppercase tracking-wide">
              Bring Your Own Key (BYOK)
            </h1>
          </div>
          <Link to="/help/openrouter-free" className={`text-xs font-bold flex items-center gap-1 ${link}`}>
            <HelpCircle size={15} /> How to get a free OpenRouter key
          </Link>
        </div>

        <p className="text-sm font-bold text-gray-800 mb-6 leading-relaxed">
          Your key unlocks AI re-generation, custom tender compilation, and investigation chat.
          Keys are stored in your browser and sent only in a request header to our API. They are never logged or stored server-side.
        </p>

        {!signedIn && (
          <div className={`${noteBox} mb-6 border-amber-500 bg-amber-50`}>
            <p className="font-bold text-amber-950 text-sm">
              Note: You are currently signed out. You can configure your key now, but signing in is required to make generation requests.
            </p>
          </div>
        )}

        {/* Existing configured key summary */}
        {llm && (
          <div className="p-4 bg-emerald-50 border-2 border-emerald-700 rounded-lg mb-6" data-testid="active-key-summary">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <span className="text-xs font-black uppercase tracking-wider text-emerald-900 block">
                  Active Configuration
                </span>
                <span className="text-sm font-bold text-emerald-950">
                  Provider: <span className="uppercase font-mono">{llm.provider ?? "Custom"}</span> · Model:{" "}
                  <span className="font-mono">{llm.model}</span>
                </span>
                <div className="text-xs font-mono font-bold text-emerald-800 mt-1">
                  Key: {maskKey(llm.key)} · {llm.remember ? "Remembered on this device" : "Session only (clears on tab close)"}
                </div>
              </div>
              <button
                type="button"
                className={btnDanger}
                onClick={handleClear}
                data-testid="forget-key-button"
              >
                <Trash2 size={15} /> Forget key
              </button>
            </div>
          </div>
        )}

        {/* Key input & detect form */}
        <div className="space-y-4">
          <div>
            <label htmlFor="ai-key" className={label}>
              Provider API Key
            </label>
            <div className="flex gap-2">
              <input
                id="ai-key"
                type="password"
                className={input}
                value={keyInput}
                onChange={(e) => {
                  setKeyInput(e.target.value);
                  if (hintRequired) setHintRequired(false);
                }}
                placeholder="Paste your API key (OpenRouter, Anthropic, Google, Groq, etc.)"
                autoComplete="off"
                spellCheck="false"
                data-testid="ai-key-input"
              />
              <button
                type="button"
                className={btnPrimary}
                onClick={() => void handleDetect()}
                disabled={detecting || !keyInput.trim()}
                data-testid="detect-key-button"
              >
                {detecting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Detecting…
                  </>
                ) : (
                  "Detect key"
                )}
              </button>
            </div>
            <p className="text-xs font-bold text-gray-600 mt-1.5">
              Supports OpenRouter, Anthropic, Google AI Studio, Groq, xAI, OpenAI, DeepSeek, and Mistral.
            </p>
          </div>

          {error && (
            <div role="alert" className={errorBox}>
              {error}
            </div>
          )}

          {/* Ambiguous Key Provider Picker */}
          {hintRequired && (
            <div className="p-4 bg-amber-50 border-2 border-amber-600 rounded-lg space-y-3" data-testid="provider-picker-box">
              <div className="flex items-center gap-2">
                <AlertTriangle size={18} className="text-amber-800 shrink-0" />
                <span className="text-xs font-black uppercase tracking-wider text-amber-950">
                  Ambiguous Key Format · Provider Selection Required
                </span>
              </div>
              <p className="text-xs font-bold text-amber-950">
                Both OpenAI and DeepSeek issue keys beginning with <code>sk-</code>. Choose which provider issued this key:
              </p>
              <div className="flex flex-wrap gap-3">
                {hintCandidates.map((cand) => {
                  const label = cand.toLowerCase() === "openai" ? "OpenAI" : cand.toLowerCase() === "deepseek" ? "DeepSeek" : cand;
                  const isSelected = selectedHint.toLowerCase() === cand.toLowerCase();
                  return (
                    <label
                      key={cand}
                      className={`flex items-center gap-2 px-3 py-2 rounded-md border-2 cursor-pointer font-bold text-sm ${
                        isSelected
                          ? "bg-amber-200 border-amber-800 text-amber-950"
                          : "bg-white border-gray-400 text-gray-800 hover:bg-gray-50"
                      }`}
                    >
                      <input
                        type="radio"
                        name="provider-hint"
                        value={cand}
                        checked={isSelected}
                        onChange={() => setSelectedHint(cand)}
                        className="accent-black"
                        data-testid={`provider-option-${cand}`}
                      />
                      <span>{label}</span>
                    </label>
                  );
                })}
              </div>
              <div>
                <button
                  type="button"
                  className={btnPrimary}
                  onClick={() => void handleDetect(selectedHint)}
                  disabled={detecting}
                  data-testid="confirm-provider-button"
                >
                  {detecting ? (
                    <>
                      <Loader2 size={16} className="animate-spin" /> Verifying with {selectedHint === "openai" ? "OpenAI" : selectedHint === "deepseek" ? "DeepSeek" : selectedHint}…
                    </>
                  ) : (
                    `Re-detect as ${selectedHint === "openai" ? "OpenAI" : selectedHint === "deepseek" ? "DeepSeek" : selectedHint}`
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Detect Result & Model Selection */}
          {detectResult && detectResult.valid && (
            <div className="p-5 bg-gray-50 border-2 border-gray-900 rounded-lg space-y-4 mt-4" data-testid="detect-result-box">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-gray-300 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-black uppercase tracking-wider text-gray-700">Provider:</span>
                  <span
                    className="px-2.5 py-0.5 bg-black text-white font-black text-xs uppercase tracking-wider rounded font-mono"
                    data-testid="provider-badge"
                  >
                    {detectResult.provider}
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-500">
                    <CheckCircle2 size={13} /> Valid
                  </span>
                </div>

                {isFree ? (
                  <span className="text-xs font-black bg-blue-100 text-blue-900 px-2.5 py-0.5 rounded border border-blue-400">
                    Free Tier Key
                  </span>
                ) : (
                  <span className="text-xs font-black bg-purple-100 text-purple-900 px-2.5 py-0.5 rounded border border-purple-400">
                    Paid Key
                  </span>
                )}
              </div>

              {/* UX adapted to free vs paid */}
              {isFree ? (
                <div className="p-3 bg-blue-50 border-2 border-blue-400 rounded-md text-xs font-bold text-blue-950 space-y-1">
                  <p className="font-black uppercase tracking-wider flex items-center gap-1">
                    <AlertTriangle size={14} className="text-blue-700" /> Free Tier Rate Limits Apply
                  </p>
                  <p>
                    Free models (variants ending in <code>:free</code>) allow up to 50 requests/day on zero-credit accounts.
                    Responses may be slower or queued during peak hours. Chat turns will be paused if your remaining daily quota is low.
                  </p>
                  {detectResult.key_info?.free_model_daily_requests && (
                    <p className="font-mono mt-1">
                      Today: {detectResult.key_info.free_model_daily_requests.used} used /{" "}
                      {detectResult.key_info.free_model_daily_requests.remaining} remaining (limit{" "}
                      {detectResult.key_info.free_model_daily_requests.limit})
                    </p>
                  )}
                </div>
              ) : (
                <div className="p-3 bg-purple-50 border-2 border-purple-400 rounded-md text-xs font-bold text-purple-950">
                  <p className="font-black uppercase tracking-wider mb-0.5">Paid Model Usage</p>
                  <p>
                    Calls will be billed directly to your provider balance according to standard model token pricing.
                    TenderFender adds zero markup.
                  </p>
                </div>
              )}

              {/* Model Picker */}
              <ModelSelect
                id="settings-model"
                models={detectResult.models}
                value={selectedModel}
                onChange={setSelectedModel}
                freeFirst={isFree}
                recommended={detectResult.recommended_model}
              />

              {/* Limitations Box */}
              {detectResult.limitations && detectResult.limitations.length > 0 && (
                <div className="border-t-2 border-gray-200 pt-3" data-testid="limitations-box">
                  <span className="text-xs font-black uppercase tracking-wider text-gray-700 block mb-1">
                    Provider Limits & Policies
                  </span>
                  <ul className="list-disc pl-5 text-xs font-bold text-gray-800 space-y-0.5">
                    {detectResult.limitations.map((lim, idx) => (
                      <li key={idx}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Remember on this device toggle */}
              <div className="border-t-2 border-gray-200 pt-3">
                <label className="flex items-start gap-3 text-sm font-bold text-gray-950 cursor-pointer">
                  <input
                    type="checkbox"
                    className="mt-0.5 w-5 h-5 accent-black"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                    data-testid="remember-key-checkbox"
                  />
                  <span>
                    Remember on this device
                  </span>
                </label>
                <div className="mt-1.5 ml-8 p-2.5 bg-amber-50 border-2 border-amber-400 rounded text-xs font-bold text-amber-950 flex items-start gap-2">
                  <ShieldAlert size={16} className="text-amber-800 shrink-0 mt-0.5" />
                  <span>
                    <strong>Warning:</strong> Storing your key persists it in this machine's <code>localStorage</code>.
                    Only tick this on your personal, trusted workstation. Never on shared or public terminals.
                  </span>
                </div>
              </div>

              {/* Save Button */}
              <div className="border-t-2 border-gray-200 pt-4 flex items-center justify-between">
                <button
                  type="button"
                  className={btnPrimary}
                  onClick={handleSave}
                  disabled={saving || !selectedModel}
                  data-testid="save-ai-settings-button"
                >
                  <Save size={16} /> Save settings
                </button>
                {savedSuccess && (
                  <span className="text-xs font-black text-emerald-800 flex items-center gap-1 font-mono">
                    <CheckCircle2 size={16} /> Settings saved!
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
