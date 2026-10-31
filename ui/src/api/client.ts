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

export interface GraphResponse {
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  highlighted_paths: HighlightedPath[];
  rings: Ring[];
  vendor_scores: Record<string, number>;
  metrics: Record<string, unknown>;
}

export interface ConfirmResponse {
  tender_id: string;
  atom_id: string;
  formalization_status: string;
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
};

export default api;

