import type { DetectResponse } from "../api/client";

// Key storage rules: sessionStorage by default; localStorage only when the user ticks
// "Remember on this device". The key is only ever sent to our own /api/* in the X-LLM-Key header.
const LLM_KEY = "tf.llm";

export interface LlmSettings {
  key: string;
  provider: string | null; // detected provider, sent as X-LLM-Provider
  model: string | null;
  remember: boolean;
  detect: DetectResponse | null; // last detect result: models, key_info, limitations
  checked_at: string; // ISO time of that detect call
}

export function loadLlmSettings(): LlmSettings | null {
  const raw = localStorage.getItem(LLM_KEY) ?? sessionStorage.getItem(LLM_KEY);
  if (!raw) return null;
  try {
    const s: LlmSettings = JSON.parse(raw);
    return typeof s.key === "string" && s.key ? s : null;
  } catch {
    return null;
  }
}

export function saveLlmSettings(s: LlmSettings): void {
  const json = JSON.stringify(s);
  if (s.remember) {
    localStorage.setItem(LLM_KEY, json);
    sessionStorage.removeItem(LLM_KEY);
  } else {
    sessionStorage.setItem(LLM_KEY, json);
    localStorage.removeItem(LLM_KEY);
  }
}

export function clearLlmSettings(): void {
  localStorage.removeItem(LLM_KEY);
  sessionStorage.removeItem(LLM_KEY);
}

// Sign-out drops the session key; a key remembered on this device stays until the user forgets it.
export function clearSessionLlmSettings(): void {
  sessionStorage.removeItem(LLM_KEY);
}

// A free OpenRouter key: OpenRouter reports is_free_tier (the account never bought credits).
export function isFreeOpenRouterKey(d: DetectResponse | null | undefined): boolean {
  return d?.provider === "openrouter" && d.key_info?.is_free_tier === true;
}

// A model is free when the provider reported it so, or it is an OpenRouter `:free` variant.
export function isFreeModel(s: LlmSettings | null): boolean {
  if (!s?.model) return false;
  const m = s.detect?.models.find((x) => x.id === s.model);
  return Boolean(m?.free || s.model.endsWith(":free"));
}

export function maskKey(key: string): string {
  return key.length <= 8 ? "••••" : `${key.slice(0, 4)}••••${key.slice(-4)}`;
}
