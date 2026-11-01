import type { AuthConfig } from "../api/client";

// Cognito managed login, authorization-code grant with PKCE (S256), public client (no secret).
const PKCE_KEY = "tf.auth.pkce";
const SCOPES = "openid email profile";

interface PendingLogin {
  verifier: string;
  state: string;
  return_to: string;
}

function base64url(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function randomToken(byteLength: number): string {
  return base64url(crypto.getRandomValues(new Uint8Array(byteLength)));
}

export function authConfigured(cfg: AuthConfig | null): cfg is AuthConfig {
  return Boolean(cfg && cfg.domain && cfg.client_id);
}

// `domain` is a bare host ("<prefix>.auth.<region>.amazoncognito.com"); tolerate a scheme or a bare prefix.
export function cognitoBaseUrl(cfg: AuthConfig): string {
  const d = cfg.domain.trim().replace(/\/+$/, "");
  if (/^https?:\/\//.test(d)) return d;
  if (!d.includes(".")) return `https://${d}.auth.${cfg.region}.amazoncognito.com`;
  return `https://${d}`;
}

export function redirectUri(cfg: AuthConfig): string {
  return window.location.origin + (cfg.redirect_path || "/auth/callback");
}

// Builds the /oauth2/authorize URL and records verifier+state for the callback in sessionStorage.
export async function buildLoginUrl(cfg: AuthConfig, returnTo: string): Promise<string> {
  const verifier = randomToken(64); // 86 chars, within RFC 7636's 43..128
  const state = randomToken(24);
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  const pending: PendingLogin = { verifier, state, return_to: returnTo };
  sessionStorage.setItem(PKCE_KEY, JSON.stringify(pending));
  const params = new URLSearchParams({
    response_type: "code",
    client_id: cfg.client_id,
    redirect_uri: redirectUri(cfg),
    scope: SCOPES,
    state,
    code_challenge: base64url(digest),
    code_challenge_method: "S256",
  });
  return `${cognitoBaseUrl(cfg)}/oauth2/authorize?${params.toString()}`;
}

export interface ExchangeResult {
  id_token: string;
  access_token?: string;
  expires_in: number;
  return_to: string;
}

// Validates state and swaps the code for tokens at /oauth2/token. The verifier is single-use.
export async function exchangeCode(cfg: AuthConfig, code: string, state: string): Promise<ExchangeResult> {
  const raw = sessionStorage.getItem(PKCE_KEY);
  sessionStorage.removeItem(PKCE_KEY);
  if (!raw) throw new Error("No sign-in in progress in this tab. Start again from Sign in.");
  const pending: PendingLogin = JSON.parse(raw);
  if (!pending.state || pending.state !== state) throw new Error("Sign-in state mismatch. Start again from Sign in.");

  const res = await fetch(`${cognitoBaseUrl(cfg)}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: cfg.client_id,
      code,
      redirect_uri: redirectUri(cfg),
      code_verifier: pending.verifier,
    }),
  });
  const body: { id_token?: string; access_token?: string; expires_in?: number; error?: string } = await res
    .json()
    .catch(() => ({}));
  if (!res.ok || !body.id_token) {
    throw new Error(`Sign-in failed at the token step${body.error ? ` (${body.error})` : ""}.`);
  }
  return {
    id_token: body.id_token,
    access_token: body.access_token,
    expires_in: body.expires_in ?? 3600,
    return_to: pending.return_to || "/",
  };
}

export function logoutUrl(cfg: AuthConfig): string {
  const params = new URLSearchParams({ client_id: cfg.client_id, logout_uri: `${window.location.origin}/` });
  return `${cognitoBaseUrl(cfg)}/logout?${params.toString()}`;
}
