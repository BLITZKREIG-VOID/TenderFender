import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  KeyRound,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Loader2,
  Trash2,
  Eye,
  EyeOff,
  ClipboardPaste,
  Info,
  X,
  ShieldCheck,
} from "lucide-react";
import { api, apiError, type DetectResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { maskKey, isFreeOpenRouterKey, type LlmSettings, clearLlmSettings } from "../auth/llmKey";
import { KEY_PRIVACY_COPY, KEY_STORAGE_WARNING } from "../auth/privacy";
import ModelSelect from "../components/ModelSelect";
import {
  panel,
  btnPrimary,
  btnSecondary,
  btnDanger,
  input,
  errorBox,
  noteBox,
  link,
} from "../components/styles";

type KeyState = "unconfigured" | "validating" | "valid" | "invalid";

export default function SettingsAi() {
  const { signedIn, llm, setLlm } = useAuth();

  const [keyInput, setKeyInput] = useState(llm?.key ?? "");
  const [showKey, setShowKey] = useState(false);
  const [canPaste, setCanPaste] = useState(false);

  // Validation is ONLY explicit on click/Enter; a remembered key is never validated automatically on load.
  const [keyState, setKeyState] = useState<KeyState>(llm?.key ? "valid" : "unconfigured");
  const [detectResult, setDetectResult] = useState<DetectResponse | null>(llm?.detect ?? null);
  const [selectedModel, setSelectedModel] = useState<string | null>(llm?.model ?? null);
  const [error, setError] = useState<string | null>(null);

  const [remember, setRemember] = useState(llm?.remember ?? false);
  const [removeOpen, setRemoveOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setCanPaste(Boolean(window.isSecureContext && typeof navigator !== "undefined" && navigator.clipboard?.readText));
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const hasRememberedKey = Boolean(llm?.key && llm?.remember);

  const handlePaste = async () => {
    if (!canPaste) return;
    try {
      const val = await navigator.clipboard.readText();
      if (val) {
        setKeyInput(val);
        setError(null);
      }
    } catch {
      // Clipboard permission refused -> fail silently.
    }
  };

  const handleValidate = async () => {
    const trimmed = keyInput.trim();
    if (!trimmed) {
      setError("Please paste an OpenRouter API key.");
      setKeyState("invalid");
      return;
    }

    setKeyState("validating");
    setError(null);

    try {
      const res = await api.detectKey({ key: trimmed, provider: "openrouter" });
      if (!res.data.valid) {
        setKeyState("invalid");
        setDetectResult(null);
        setError("Check the key and try again.");
      } else {
        setKeyState("valid");
        setDetectResult(res.data);
        const rec = res.data.recommended_model || res.data.models[0]?.id || null;
        setSelectedModel(rec);
        const settings: LlmSettings = {
          key: trimmed,
          provider: "openrouter",
          model: rec,
          remember,
          detect: res.data,
          checked_at: new Date().toISOString(),
        };
        setLlm(settings);
      }
    } catch (err) {
      setKeyState("invalid");
      setDetectResult(null);
      const info = apiError(err, "Validation failed");
      if (info.code === "openrouter_key_required" || info.message?.includes("Only OpenRouter")) {
        setError("Only OpenRouter keys are supported.");
      } else {
        setError(info.message ? `${info.message} Check the key and try again.` : "Check the key and try again.");
      }
    }
  };

  const handleToggleRemember = (checked: boolean) => {
    setRemember(checked);
    if (llm) {
      setLlm({
        ...llm,
        remember: checked,
      });
    }
  };

  const handleClear = () => {
    setKeyInput("");
    setError(null);
    if (!hasRememberedKey) {
      setKeyState("unconfigured");
      clearLlmSettings();
      setLlm(null);
      setDetectResult(null);
      setSelectedModel(null);
    } else if (keyState === "invalid") {
      setKeyState("valid");
    }
  };

  const confirmRemove = () => {
    clearLlmSettings();
    setLlm(null);
    setKeyInput("");
    setDetectResult(null);
    setSelectedModel(null);
    setKeyState("unconfigured");
    setRemember(false);
    setRemoveOpen(false);
    setError(null);
  };

  const isFree = isFreeOpenRouterKey(detectResult);

  const renderStatusPill = () => {
    if (keyState === "validating") {
      return (
        <span
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-amber-100 text-amber-950 border-2 border-amber-500"
          data-testid="status-pill"
        >
          <Loader2 size={13} className="animate-spin text-amber-800" aria-hidden="true" />
          Validating
        </span>
      );
    }
    if (keyState === "valid") {
      return (
        <span
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-emerald-100 text-emerald-950 border-2 border-emerald-600"
          data-testid="status-pill"
        >
          <ShieldCheck size={14} className="text-emerald-700" aria-hidden="true" />
          Connected
        </span>
      );
    }
    if (keyState === "invalid") {
      return (
        <span
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-red-100 text-red-950 border-2 border-red-600"
          data-testid="status-pill"
        >
          <span className="w-2 h-2 rounded-full bg-red-600" aria-hidden="true" />
          Invalid API key
        </span>
      );
    }
    return (
      <span
        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-amber-100 text-amber-950 border-2 border-amber-500"
        data-testid="status-pill"
      >
        <KeyRound size={13} className="text-amber-800" aria-hidden="true" />
        API key required
      </span>
    );
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6" data-testid="settings-ai-page">
      <div className={panel}>
        {/* Header */}
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

        <p className="text-sm font-bold text-gray-800 mb-4 leading-relaxed" data-testid="ai-modes-explainer">
          AI re-generation, custom tender compilation and investigation chat run with your own OpenRouter API key.
          Requests go to OpenRouter and are billed to your account or covered under free community models.
          Keys are stored in your browser and sent only in a request header to our API. They are never logged or stored server-side.
        </p>

        <p className="text-xs font-medium text-gray-600 leading-relaxed mb-6" data-testid="privacy-notice">
          {KEY_PRIVACY_COPY}
        </p>

        {!signedIn && (
          <div className={`${noteBox} mb-6 border-amber-500 bg-amber-50`}>
            <p className="font-bold text-amber-950 text-sm">
              Note: You are currently signed out. You can configure your key now, but signing in is required to make generation requests.
            </p>
          </div>
        )}

        {/* Key Card */}
        <div className="p-5 bg-white border-2 border-gray-900 rounded-xl shadow-xs space-y-4">
          {/* Card Title & Status Pill */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-gray-200 pb-3">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-black text-black uppercase tracking-wide">
                OpenRouter API key
              </h2>
              <details className="group relative">
                <summary
                  className="flex h-7 w-7 cursor-pointer list-none items-center justify-center rounded-full text-gray-700 outline-none hover:bg-gray-100 hover:text-black focus-visible:ring-2 focus-visible:ring-blue-600 [&::-webkit-details-marker]:hidden"
                  aria-label="How to get an OpenRouter key"
                  title="How to get an OpenRouter key"
                >
                  <Info size={16} aria-hidden="true" />
                </summary>
                <div className="absolute left-0 top-full z-40 mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-xl border-2 border-black bg-white p-4 text-xs leading-5 text-black shadow-xl">
                  <h3 className="font-black text-sm uppercase tracking-wide">
                    How to get an OpenRouter key
                  </h3>
                  <ol className="mt-2 list-decimal space-y-1.5 pl-4 font-semibold text-gray-800">
                    <li>Open OpenRouter and sign in (or create a free account).</li>
                    <li>Open <span className="font-bold">Keys</span> and create a key.</li>
                    <li>Copy the key and paste it into this field.</li>
                  </ol>
                  <a
                    href="https://openrouter.ai/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 bg-black text-white rounded font-bold text-xs uppercase tracking-wider hover:bg-gray-800 focus:outline-hidden focus:ring-2 focus:ring-blue-600"
                  >
                    Open OpenRouter Keys
                  </a>
                  <p className="mt-2 text-[11px] font-bold text-gray-600">
                    Models ending in :free cost nothing but have rate limits.
                  </p>
                </div>
              </details>
            </div>
            <div>{renderStatusPill()}</div>
          </div>

          {/* Password Input & Action Buttons */}
          <div className="flex flex-col gap-2 sm:flex-row items-stretch sm:items-center">
            <div className="relative min-w-0 flex-1">
              <input
                id="openrouter-key"
                type={showKey ? "text" : "password"}
                value={keyInput}
                onChange={(e) => {
                  setKeyInput(e.target.value);
                  if (error) setError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    void handleValidate();
                  }
                }}
                autoComplete="off"
                spellCheck={false}
                placeholder="Paste your OpenRouter API key..."
                disabled={keyState === "validating"}
                className={`${input} pr-10`}
                aria-label="OpenRouter API key"
                data-testid="openrouter-key-input"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                aria-label={showKey ? "Hide OpenRouter API key" : "Show OpenRouter API key"}
                title={showKey ? "Hide key" : "Show key"}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-600 hover:text-black focus:outline-hidden focus:ring-2 focus:ring-blue-600 rounded"
              >
                {showKey ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
              </button>
            </div>

            {canPaste && (
              <button
                type="button"
                onClick={() => void handlePaste()}
                disabled={keyState === "validating"}
                aria-label="Paste OpenRouter API key"
                title="Paste key"
                className={btnSecondary}
                data-testid="paste-key-button"
              >
                <ClipboardPaste size={16} aria-hidden="true" />
                <span className="hidden sm:inline">Paste</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => void handleValidate()}
              disabled={!keyInput.trim() || keyState === "validating"}
              className={btnPrimary}
              data-testid="validate-connect-button"
            >
              {keyState === "validating" ? (
                <>
                  <Loader2 size={16} className="animate-spin" aria-hidden="true" /> Validating…
                </>
              ) : (
                "Validate & Connect"
              )}
            </button>

            <button
              type="button"
              onClick={handleClear}
              disabled={!keyInput && keyState !== "valid"}
              aria-label="Clear OpenRouter key"
              title="Clear key"
              className={btnSecondary}
              data-testid="clear-key-button"
            >
              <Trash2 size={16} aria-hidden="true" />
            </button>
          </div>

          {/* Error Alert Box */}
          {error && (
            <div role="alert" className={errorBox} data-testid="key-error-alert">
              {error}
            </div>
          )}

          {/* Remember Key Checkbox & Confirmation */}
          <div className="mt-3 p-3 bg-gray-50 border-2 border-gray-300 rounded-lg">
            <label htmlFor="remember-key" className="flex items-start gap-3 cursor-pointer">
              <input
                id="remember-key"
                type="checkbox"
                checked={remember}
                onChange={(e) => handleToggleRemember(e.target.checked)}
                className="mt-0.5 w-4 h-4 accent-black"
                data-testid="remember-key-checkbox"
              />
              <span className="min-w-0">
                <span className="block text-sm font-bold text-gray-950">
                  Remember key on this device
                </span>
                <span className="block text-xs font-semibold text-gray-600 mt-0.5">
                  {KEY_STORAGE_WARNING}
                </span>
              </span>
            </label>

            {hasRememberedKey && !removeOpen && (
              <div className="mt-3 pt-2 border-t border-gray-300">
                <button
                  type="button"
                  onClick={() => setRemoveOpen(true)}
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-red-700 hover:text-red-900 focus:outline-hidden focus:ring-2 focus:ring-red-500 rounded p-1"
                  data-testid="remove-saved-key-button"
                >
                  <Trash2 size={13} aria-hidden="true" /> Remove saved key
                </button>
              </div>
            )}

            {removeOpen && (
              <div
                className="mt-3 p-3 bg-red-50 border-2 border-red-600 rounded-lg"
                role="alertdialog"
                aria-labelledby="remove-key-title"
                aria-describedby="remove-key-description"
                data-testid="remove-key-dialog"
              >
                <div className="flex items-start gap-2">
                  <Trash2 size={16} className="text-red-700 shrink-0 mt-0.5" aria-hidden="true" />
                  <div className="min-w-0">
                    <p id="remove-key-title" className="text-sm font-bold text-red-950">
                      Remove this saved key?
                    </p>
                    <p id="remove-key-description" className="mt-1 text-xs text-red-900">
                      TenderFender will stop remembering it on this browser. You can connect again anytime.
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={confirmRemove}
                        className={btnDanger}
                        data-testid="confirm-remove-button"
                      >
                        Remove key
                      </button>
                      <button
                        type="button"
                        onClick={() => setRemoveOpen(false)}
                        className={btnSecondary}
                        data-testid="cancel-remove-button"
                      >
                        <X size={14} aria-hidden="true" /> Keep key
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Connected Details & Model Picker */}
          {keyState === "valid" && detectResult && (
            <div className="mt-5 p-5 bg-gray-50 border-2 border-gray-900 rounded-lg space-y-4" data-testid="detect-result-box">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-gray-300 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-black uppercase tracking-wider text-gray-700">Provider:</span>
                  <span
                    className="px-2.5 py-0.5 bg-black text-white font-black text-xs uppercase tracking-wider rounded font-mono"
                    data-testid="provider-badge"
                  >
                    OpenRouter
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-500">
                    <CheckCircle2 size={13} /> Connected
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

              <div className="text-xs font-mono font-bold text-gray-800">
                Key: {maskKey(llm?.key || keyInput)} · {remember ? "Remembered on this device" : "Session only (clears on tab close)"}
              </div>

              {isFree ? (
                <div className="p-3 bg-blue-50 border-2 border-blue-400 rounded-md text-xs font-bold text-blue-950 space-y-1">
                  <p className="font-black uppercase tracking-wider flex items-center gap-1">
                    <AlertTriangle size={14} className="text-blue-700" /> Free Tier Rate Limits Apply
                  </p>
                  <p>Models ending in :free cost nothing but have rate limits.</p>
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
                    Calls will be billed directly to your OpenRouter balance according to standard model token pricing.
                    TenderFender adds zero markup.
                  </p>
                </div>
              )}

              {detectResult.models && detectResult.models.length > 0 && (
                <ModelSelect
                  id="settings-model"
                  models={detectResult.models}
                  value={selectedModel}
                  onChange={(m) => {
                    setSelectedModel(m);
                    if (llm) {
                      setLlm({ ...llm, model: m });
                    }
                  }}
                  freeFirst={isFree}
                  recommended={detectResult.recommended_model}
                />
              )}

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
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
