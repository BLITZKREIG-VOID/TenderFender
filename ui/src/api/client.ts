import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

export interface TenderSummary {
  tender_id: string;
  title: string;
  risk_level: "low" | "medium" | "high";
  decision: "clear" | "review" | "escalate";
}

export interface Atom {
  id: string;
  clause_id: string;
  field: string;
  op: string;
  value: number | string | string[];
  source_text: string;
  formalization_status?: string;
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

export interface AnalysisResponse {
  fused: FusedData;
  rules: RulesData;
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
}

export interface ConfirmResponse {
  tender_id: string;
  atom_id: string;
  formalization_status: string;
}

// ── API calls ──────────────────────────────────────────────────────────────

// Module-level session cache: makes revisiting a tender instant. Entries are
// dropped whenever the underlying server state changes (confirm/refresh).
const payloadCache = new Map<string, unknown>();

function cached<T>(key: string): T | undefined {
  return payloadCache.get(key) as T | undefined;
}

export const api = {
  getHealth: () => client.get<{ status: string; mode: string }>("/health"),

  getTenders: () => client.get<TenderSummary[]>("/tenders"),

  getAnalysis: async (id: string): Promise<{ data: AnalysisResponse }> => {
    const key = `analysis-${id}`;
    const hit = cached<AnalysisResponse>(key);
    if (hit !== undefined) return { data: hit };

    const response = await client.get<AnalysisResponse>(
      `/tenders/${id}/analysis`
    );
    payloadCache.set(key, response.data);
    return { data: response.data };
  },

  getGraph: async (id: string): Promise<{ data: GraphResponse }> => {
    const key = `graph-${id}`;
    const hit = cached<GraphResponse>(key);
    if (hit !== undefined) return { data: hit };

    const response = await client.get<GraphResponse>(`/tenders/${id}/graph`);
    payloadCache.set(key, response.data);
    return { data: response.data };
  },

  confirmAtom: async (tenderId: string, atomId: string) => {
    const response = await client.post<ConfirmResponse>(
      `/tenders/${tenderId}/atoms/${atomId}/confirm`
    );
    // Confirmation mutates server-side rules state, so the cached analysis is stale.
    payloadCache.delete(`analysis-${tenderId}`);
    return response;
  },

  // Manual refresh must bypass the session cache.
  invalidateTender: (id: string) => {
    payloadCache.delete(`analysis-${id}`);
    payloadCache.delete(`graph-${id}`);
  },
};

export default api;

