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
};

export default api;

