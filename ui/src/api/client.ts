import axios from "axios";
import { getIdToken, clearTokens } from "../auth/tokens";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// The Cognito id token rides on every /api call once signed in; public endpoints ignore it.
client.interceptors.request.use((config) => {
  const token = getIdToken();
  if (token) config.headers.set("Authorization", `Bearer ${token}`);
  return config;
});

// A 401 means the token is expired or revoked: drop it so the UI falls back to signed-out prompts.
client.interceptors.response.use(undefined, (err) => {
  if (err?.response?.status === 401 && getIdToken()) {
    clearTokens();
    window.dispatchEvent(new Event("tf-auth-changed"));
  }
  return Promise.reject(err);
});

export interface TenderSummary {
  tender_id: string;
  title: string;
  risk_level: "low" | "medium" | "high";
  decision: "clear" | "review" | "escalate";
  source: TenderSource;
}

export type TenderSource = "real" | "synthetic_demo";

export interface NetworkCheck {
  status: "not_applicable";
  reason: string;
}

export interface Atom {
  id: string;
  clause_id: string;
  field: string;
  op: string;
  value: number | string | string[];
  source_text: string;
}

export interface Finding {
  finding_id: string;
  type: string;
  severity: string;
  clause_ids: string[];
  source_texts: string[];
  proof: { method: string; detail: string };
  explanation: string;
}

export interface RulesData {
  tender_id: string;
  formalization_status: string;
  atoms: Atom[];
  findings: Finding[];
  qualifying_vendors: string[];
  vendors_evaluated: number;
  not_checked?: NotChecked[];
  vendor_check?: { status: "run" | "skipped"; reason: string };
}

export interface NotChecked {
  clause_id: string;
  text: string;
  reason: string;
}

export interface Citation {
  ref: string;
  kind: "guideline" | "finding" | "ring";
  source_title?: string;
  source_url?: string;
  section?: string;
}

export interface LinkedVendor {
  vendor_id: string;
  reason: string;
  ring_id: string;
  path: string[];
}

export interface FusedData {
  tender_id: string;
  title: string;
  risk_level: "low" | "medium" | "high";
  decision: "clear" | "review" | "escalate";
  rule_finding_ids: string[];
  graph_flag_ring_ids: string[];
  linked_vendors: LinkedVendor[];
  source?: TenderSource;
  network_check?: NetworkCheck;
  summary: string;
  reasoning: string;
  citations: Citation[];
  recommended_actions: string[];
  decision_source: string;
  disclaimer: string;
}

export interface Clause {
  clause_id: string;
  text: string;
  source_clause_no?: string;
  needs_review?: boolean;
}

export interface Passage {
  passage_id: string;
  source_title?: string;
  source_url?: string;
  section?: string;
  retrieved?: string;
  topics?: string[];
  text?: string;
  missing?: boolean;
}

export interface AtomStatusEntry {
  status: "confirmed" | "rejected" | "undecided";
  note: string;
  at: string | null;
}

export interface AnalysisResponse {
  source: TenderSource;
  source_portal?: string | null;
  source_url?: string | null;
  source_ref?: string | null;
  retrieved?: string | null;
  attribution?: string | null;
  fused: FusedData;
  rules: RulesData;
  atom_status: Record<string, AtomStatusEntry>;
  clauses: Clause[];
  passages: Passage[];
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  flagged: boolean;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface HighlightedPath {
  from: string;
  to: string;
  nodes: string[];
  edge_types: string[];
}

export interface Ring {
  ring_id: string;
  vendor_ids: string[];
  link_types: string[];
  score: number;
}

export interface GraphMetricScores {
  pr_auc?: number;
  precision_at_10?: number;
}

export interface GraphMetrics {
  baseline?: GraphMetricScores;
  gnn?: GraphMetricScores;
  gnn_status?: string;
  note?: string;
}

export interface GraphResponse {
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  highlighted_paths: HighlightedPath[];
  rings: Ring[];
  vendor_scores: Record<string, number>;
  metrics: GraphMetrics;
  network_check?: NetworkCheck;
}

export interface ConfirmResponse {
  tender_id: string;
  atom_id: string;
  formalization_status: string;
}

// ── Accounts + BYOK (see ACCOUNTS_BYOK spec) ────────────────────────────────

export interface AuthConfig {
  region: string;
  user_pool_id: string;
  client_id: string;
  domain: string;
  redirect_path: string;
}

export type Role =
  | "procurement_officer"
  | "auditor_vigilance"
  | "journalist"
  | "researcher_student"
  | "vendor_contractor"
  | "citizen"
  | "other";
export type OrgType =
  | "central_govt"
  | "state_govt"
  | "psu"
  | "private"
  | "ngo_media"
  | "academic"
  | "individual";
export type Purpose = "check_my_tenders" | "audit_oversight" | "research" | "learning" | "other";
export type Experience = "new" | "some" | "expert";

export interface ProfileInput {
  role: Role;
  org_type: OrgType;
  state: string;
  purpose: Purpose;
  experience: Experience;
  consent: true;
}

export interface Profile extends ProfileInput {
  updated_at?: string;
}

export interface UsageCounters {
  regen: number;
  compile: number;
  chat: number;
}

export interface Me {
  user_id: string;
  email: string;
  name: string;
  profile: Profile | null;
  usage: UsageCounters;
  limits: UsageCounters;
  reset_at?: string;
}

export interface LlmModel {
  id: string;
  name: string;
  context_length: number | null;
  free: boolean;
}

// Whitelisted pass-through of OpenRouter's GET /api/v1/key `data` fields, each only when present.
export interface KeyInfo {
  is_free_tier?: boolean;
  limit?: number | null;
  limit_remaining?: number | null;
  limit_reset?: string | null;
  usage?: number;
  usage_daily?: number;
  usage_weekly?: number;
  usage_monthly?: number;
  rate_limit?: unknown;
  free_model_daily_requests?: { used: number; limit: number; remaining: number };
}

// Rejected keys come back 200 with valid:false; provider may be null when undetectable.
export interface DetectResponse {
  provider: string | null;
  valid: boolean;
  models: LlmModel[];
  key_info: KeyInfo | null;
  limitations: string[];
  recommended_model: string | null;
}

export interface RegenerateResponse {
  reasoning: string;
  recommended_actions: string[];
  citations: Citation[];
  model: string;
  provider: string;
  decision_source: "user_llm";
  validated: true;
  retrieval?: "saved" | "keyword";
}

export interface CompileResponse {
  tender_id: string;
  title?: string;
  created_at?: string;
  clauses: Clause[];
  atoms: Atom[];
  not_checked: NotChecked[];
  findings: Finding[];
  vendor_check: { status: "run" | "skipped"; reason: string };
}

export interface MyTenderSummary {
  tender_id: string;
  title: string;
  created_at?: string;
  findings_count?: number;
  model?: string;
  provider?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
}

// The user's key goes only to our own /api in a header, never in a body, URL or log.
export interface LlmCreds {
  key: string;
  provider?: string;
}

const keyHeaders = (c: LlmCreds) => {
  const h: Record<string, string> = { "X-LLM-Key": c.key };
  if (c.provider) h["X-LLM-Provider"] = c.provider;
  return { headers: h };
};

export interface ApiErrorInfo {
  status?: number;
  code?: string;
  message: string;
  limit?: number;
  reset_at?: string;
  provider_message?: string;
}

const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);

const str = (r: Record<string, unknown>, k: string): string | undefined =>
  typeof r[k] === "string" ? (r[k] as string) : undefined;

// The app wraps errors as {detail:{error,code,...}}; FastAPI validation errors put a list under detail.
export function apiError(err: unknown, fallback = "Request failed"): ApiErrorInfo {
  const info: ApiErrorInfo = { message: fallback };
  if (!isRecord(err)) return info;
  if (typeof err.message === "string" && err.message) info.message = err.message;
  const response = err.response;
  if (!isRecord(response)) return info;
  if (typeof response.status === "number") info.status = response.status;
  const data = response.data;
  const detail = isRecord(data) && "detail" in data ? data.detail : data;
  if (Array.isArray(detail)) {
    const msgs = detail.map((d) => (isRecord(d) ? str(d, "msg") : undefined)).filter(Boolean);
    if (msgs.length) info.message = msgs.join("; ");
  } else if (isRecord(detail)) {
    info.message = str(detail, "error") ?? info.message;
    info.code = str(detail, "code");
    info.reset_at = str(detail, "reset_at");
    info.provider_message = str(detail, "provider_message");
    if (typeof detail.limit === "number") info.limit = detail.limit;
  } else if (typeof detail === "string" && detail) {
    info.message = detail;
  }
  return info;
}

// One readable line for an error, including the daily-limit reset time.
export function describeError(e: ApiErrorInfo): string {
  if (e.code === "daily_limit") {
    const when = e.reset_at ? new Date(e.reset_at).toLocaleString() : "the next UTC day";
    return `Daily limit reached${e.limit != null ? ` (${e.limit} per day)` : ""}. It resets at ${when}.`;
  }
  if (e.code === "unauthenticated") return "Your session has expired. Please sign in again.";
  return e.provider_message ? `${e.message} Provider said: ${e.provider_message}` : e.message;
}

// ── API calls ──────────────────────────────────────────────────────────────

export const api = {
  getHealth: () => client.get<{ status: string; mode: string }>("/health"),

  getTenders: () => client.get<TenderSummary[]>("/tenders"),

  getAnalysis: (id: string) =>
    client.get<AnalysisResponse>(`/tenders/${id}/analysis`),

  getGraph: (id: string) =>
    client.get<GraphResponse>(`/tenders/${id}/graph`),

  confirmAtom: (tenderId: string, atomId: string) =>
    client.post<ConfirmResponse>(
      `/tenders/${tenderId}/atoms/${atomId}/confirm`
    ),

  rejectAtom: (tenderId: string, atomId: string, note: string) =>
    client.post<ConfirmResponse>(
      `/tenders/${tenderId}/atoms/${atomId}/reject`,
      { note }
    ),

  getAuthConfig: () => client.get<AuthConfig>("/auth/config"),

  getMe: () => client.get<Me>("/me"),

  putProfile: (profile: ProfileInput) => client.put<Profile>("/me/profile", profile),

  deleteMe: () => client.delete<void>("/me"),

  detectKey: (c: LlmCreds) => client.post<DetectResponse>("/llm/detect", {}, keyHeaders(c)),

  regenerate: (tenderId: string, model: string, c: LlmCreds) =>
    client.post<RegenerateResponse>(
      `/tenders/${encodeURIComponent(tenderId)}/regenerate`,
      { model },
      keyHeaders(c)
    ),

  compile: (body: { title: string; text: string; model: string }, c: LlmCreds) =>
    client.post<CompileResponse>("/compile", body, keyHeaders(c)),

  getMyTenders: () =>
    client
      .get<MyTenderSummary[] | { tenders: MyTenderSummary[] }>("/me/tenders")
      .then((r) => (Array.isArray(r.data) ? r.data : r.data.tenders ?? [])),

  getMyTender: (uid: string) =>
    client.get<CompileResponse>(`/me/tenders/${encodeURIComponent(uid)}`),

  deleteMyTender: (uid: string) => client.delete<void>(`/me/tenders/${encodeURIComponent(uid)}`),

  chat: (tenderId: string, model: string, messages: ChatMessage[], c: LlmCreds) =>
    client.post<ChatResponse>(
      `/tenders/${encodeURIComponent(tenderId)}/chat`,
      { model, messages },
      keyHeaders(c)
    ),
};

export default api;

