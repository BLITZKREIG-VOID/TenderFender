// Cognito tokens live in sessionStorage only (cleared when the tab closes). Never logged.
const TOKENS_KEY = "tf.auth.tokens";

export interface StoredTokens {
  id_token: string;
  access_token?: string;
  expires_at: number; // epoch ms
}

// Reads the unverified JWT payload; the API verifies signatures, the UI only needs exp/email.
export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const part = token.split(".")[1];
  if (!part) return null;
  try {
    const b64 = part.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(part.length / 4) * 4, "=");
    const json = new TextDecoder().decode(Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)));
    const payload: unknown = JSON.parse(json);
    return typeof payload === "object" && payload !== null ? (payload as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

export function saveTokens(idToken: string, accessToken: string | undefined, expiresInSec: number): void {
  const exp = decodeJwtPayload(idToken)?.exp;
  const expiresAt = typeof exp === "number" ? exp * 1000 : Date.now() + expiresInSec * 1000;
  const stored: StoredTokens = { id_token: idToken, access_token: accessToken, expires_at: expiresAt };
  sessionStorage.setItem(TOKENS_KEY, JSON.stringify(stored));
}

export function clearTokens(): void {
  sessionStorage.removeItem(TOKENS_KEY);
}

// Returns the id token if present and not expired (30 s skew); expired tokens are dropped.
export function getIdToken(): string | null {
  const raw = sessionStorage.getItem(TOKENS_KEY);
  if (!raw) return null;
  try {
    const t: StoredTokens = JSON.parse(raw);
    if (typeof t.id_token !== "string" || typeof t.expires_at !== "number") throw new Error("bad");
    if (t.expires_at - 30_000 <= Date.now()) {
      clearTokens();
      return null;
    }
    return t.id_token;
  } catch {
    clearTokens();
    return null;
  }
}
