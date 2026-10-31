import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import type { GraphResponse } from "../api/client";
import { Network, ZoomIn, ZoomOut, Maximize2, Info } from "lucide-react";

interface Props {
  data: GraphResponse | null;
  /** Red accents are reserved for high-risk or escalate tenders. */
  isDanger?: boolean;
}

// Projector-grade high contrast color palette
const NODE_COLORS: Record<string, { bg: string; border: string; text: string; label: string }> = {
  vendor: { bg: "#1d4ed8", border: "#1e3a8a", text: "#ffffff", label: "Vendor Firm" },
  person: { bg: "#7c3aed", border: "#4c1d95", text: "#ffffff", label: "Director / Person" },
  address: { bg: "#d97706", border: "#78350f", text: "#ffffff", label: "Registered Address" },
  buyer: { bg: "#047857", border: "#064e3b", text: "#ffffff", label: "Buyer Dept" },
};

const FLAGGED_COLOR = "#b91c1c"; // deep red
const HIGHLIGHT_COLOR = "#dc2626"; // bright vibrant red

const formatMetric = (value?: number) =>
  typeof value === "number" ? value.toFixed(2) : "—";

export default function GraphPanel({ data, isDanger = false }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [selectedNodeInfo, setSelectedNodeInfo] = useState<{ id: string; label: string; type: string; flagged: boolean } | null>(null);

  useEffect(() => {
    if (!data || !containerRef.current) return;

    // Collect set of nodes and edges involved in highlighted cartel paths
    const highlightedNodes = new Set<string>();
    const highlightedEdges = new Set<string>();

    for (const path of data.highlighted_paths || []) {
      for (const nodeId of path.nodes) {
        highlightedNodes.add(nodeId);
      }
      for (let i = 0; i < path.nodes.length - 1; i++) {
        highlightedEdges.add(`${path.nodes[i]}-${path.nodes[i + 1]}`);
        highlightedEdges.add(`${path.nodes[i + 1]}-${path.nodes[i]}`);
      }
    }

    const elements: cytoscape.ElementDefinition[] = [];

    // Construct Cytoscape nodes
    for (const node of data.graph.nodes || []) {
      const isHighlighted = highlightedNodes.has(node.id);
      elements.push({
        data: {
          id: node.id,
          label: `${node.id}\n${node.label}`,
          nodeType: node.type,
          flagged: node.flagged,
          highlighted: isHighlighted,
          rawLabel: node.label,
        },
      });
    }

    // Construct Cytoscape edges
    for (const edge of data.graph.edges || []) {
      const edgeKey1 = `${edge.source}-${edge.target}`;
      const edgeKey2 = `${edge.target}-${edge.source}`;
      const isHighlighted = highlightedEdges.has(edgeKey1) || highlightedEdges.has(edgeKey2);

      elements.push({
        data: {
          id: `${edge.source}->${edge.target}`,
          source: edge.source,
          target: edge.target,
          label: edge.type.replace(/_/g, " ").toUpperCase(),
          highlighted: isHighlighted,
        },
      });
    }

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    // Create Cytoscape instance configured for high-contrast projector display
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-wrap": "wrap",
            "text-max-width": "120px",
            "font-size": "11px",
            "font-weight": "bold",
            "font-family": "system-ui, -apple-system, sans-serif",
            color: "#000000",
            "text-valign": "bottom",
            "text-margin-y": 8,
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.85,
            "text-background-padding": "3px",
            "text-background-shape": "roundrectangle",
            width: 44,
            height: 44,
            "background-color": (ele: cytoscape.NodeSingular) => {
              if (ele.data("flagged")) return FLAGGED_COLOR;
              const typeCfg = NODE_COLORS[ele.data("nodeType")];
              return typeCfg ? typeCfg.bg : "#374151";
            },
            "border-width": (ele: cytoscape.NodeSingular) =>
              ele.data("flagged") ? 4 : 2.5,
            "border-color": (ele: cytoscape.NodeSingular) =>
              ele.data("flagged") ? "#7f1d1d" : "#000000",
          },
        },
        {
          // Nodes on a highlighted cartel path (highlighted_paths[].nodes)
          selector: "node[?highlighted]",
          style: {
            "background-color": HIGHLIGHT_COLOR,
            width: 52,
            height: 52,
            "border-width": 6,
            "border-color": "#450a0a",
            "overlay-color": "#fca5a5",
            "overlay-opacity": 0.35,
            "overlay-padding": 6,
            "z-index": 10,
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 6,
            "border-color": "#fbbf24", // bright gold outline when selected
          },
        },
        {
          selector: "edge",
          style: {
            label: "data(label)",
            "font-size": "9px",
            "font-weight": "bold",
            "font-family": "monospace",
            color: "#000000",
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.9,
            "text-background-padding": "2px",
            "text-rotation": "autorotate",
            width: 2,
            "line-color": "#475569",
            "target-arrow-color": "#475569",
            "target-arrow-shape": "triangle",
            "arrow-scale": 1.4,
            "curve-style": "bezier",
          },
        },
        {
          // Edges between consecutive nodes of a highlighted cartel path
          selector: "edge[?highlighted]",
          style: {
            width: 6,
            "line-color": HIGHLIGHT_COLOR,
            "target-arrow-color": HIGHLIGHT_COLOR,
            "arrow-scale": 1.8,
            "overlay-color": "#fca5a5",
            "overlay-opacity": 0.3,
            "overlay-padding": 3,
            "z-index": 9,
          },
        },
      ],
      layout: {
        name: "cose",
        idealEdgeLength: 100,
        nodeOverlap: 20,
        refresh: 20,
        fit: true,
        padding: 30,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        // Run synchronously: the layout animation loop does not survive an
        // instance teardown (React StrictMode mounts effects twice).
        animate: false,
      },
    });

    cyRef.current = cy;

    // Handle node selection for inspection
    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      setSelectedNodeInfo({
        id: node.data("id"),
        label: node.data("rawLabel"),
        type: node.data("nodeType"),
        flagged: Boolean(node.data("flagged") || node.data("highlighted")),
      });
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        setSelectedNodeInfo(null);
      }
    });

    return () => {
      cyRef.current = null;
      cy.destroy();
    };
  }, [data]);

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.25);
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
    }
  };

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 30);
    }
  };

  if (!data || !data.graph?.nodes || data.graph.nodes.length === 0) {
    return (
      <div className="flex flex-col justify-between rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div>
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-800">
            <Network size={20} className="text-slate-500" />
            Cartel & Collusion Network Graph
          </h2>
          <div className="rounded-lg border border-dashed border-gray-300 bg-slate-50 p-8 text-center">
            <p className="text-sm text-slate-500">No graph entities recorded for this tender.</p>
          </div>
        </div>
      </div>
    );
  }

  const metrics = data.metrics;
  const gnnStatus = metrics?.gnn_status;
  const gnnSkipped = gnnStatus === "skipped";

  return (
    <div className="flex flex-col justify-between rounded-xl border border-gray-200 bg-white p-6 text-slate-900 shadow-sm">
      <div>
        {/* Header with Title and Graph Controls */}
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 pb-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-800">
            <Network size={20} className="text-slate-500" />
            Cartel & Collusion Network Graph
          </h2>

          <div className="flex items-center gap-1 rounded-lg border border-gray-200 bg-slate-50 p-1">
            <button
              onClick={handleZoomIn}
              aria-label="Zoom in graph"
              title="Zoom In"
              className="cursor-pointer rounded-md p-1.5 text-slate-500 transition-colors hover:bg-white hover:text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
            >
              <ZoomIn size={18} />
            </button>
            <button
              onClick={handleZoomOut}
              aria-label="Zoom out graph"
              title="Zoom Out"
              className="cursor-pointer rounded-md p-1.5 text-slate-500 transition-colors hover:bg-white hover:text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
            >
              <ZoomOut size={18} />
            </button>
            <button
              onClick={handleFit}
              aria-label="Reset zoom and fit all elements"
              title="Fit to Screen"
              className="cursor-pointer rounded-md p-1.5 text-slate-500 transition-colors hover:bg-white hover:text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
            >
              <Maximize2 size={18} />
            </button>
          </div>
        </div>

        {/* Display Legend */}
        <div className="mb-5 rounded-lg border border-gray-200 bg-slate-50 p-4">
          <span className="mb-3 block text-xs font-medium text-slate-500">
            Display Legend & Node Classes
          </span>
          <div className="flex flex-wrap items-center gap-2.5 text-xs font-medium text-slate-600">
            {Object.entries(NODE_COLORS).map(([type, cfg]) => (
              <span key={type} className="inline-flex items-center gap-2 rounded-md border border-gray-200 bg-white px-2.5 py-1">
                <span
                  className="inline-block h-3.5 w-3.5 shrink-0 rounded-full shadow-sm"
                  style={{ backgroundColor: cfg.bg }}
                />
                <span className="capitalize">{type}</span>
              </span>
            ))}
            <span
              className={`inline-flex items-center gap-2 rounded-md border px-2.5 py-1 ${
                isDanger
                  ? "border-red-200 bg-red-50 text-red-700"
                  : "border-amber-200 bg-amber-50 text-amber-700"
              }`}
            >
              <span
                className="inline-block h-3.5 w-3.5 shrink-0 rounded-full shadow-sm"
                style={{ backgroundColor: FLAGGED_COLOR }}
              />
              <span className="font-medium">Flagged Ring Entity</span>
            </span>
            <span
              className={`inline-flex items-center gap-2 rounded-md border px-2.5 py-1 ${
                isDanger
                  ? "border-red-200 bg-red-50 text-red-700"
                  : "border-amber-200 bg-amber-50 text-amber-700"
              }`}
            >
              <span
                className="inline-block h-3.5 w-3.5 shrink-0 rounded-full shadow-sm"
                style={{ backgroundColor: HIGHLIGHT_COLOR }}
              />
              <span className="font-medium">Highlighted Cartel Path</span>
            </span>
          </div>
        </div>

        {/* Model Metrics & GNN Status */}
        <div className="mb-5 flex flex-wrap items-center gap-2 text-xs font-medium">
          <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
            Model Metrics
          </span>

          {metrics?.baseline && (
            <span className="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-slate-600">
              Baseline: PR-AUC{" "}
              <span className="font-mono">{formatMetric(metrics.baseline.pr_auc)}</span>
              {" · "}P@10{" "}
              <span className="font-mono">{formatMetric(metrics.baseline.precision_at_10)}</span>
            </span>
          )}

          {gnnSkipped ? (
            <div
              className="group relative inline-flex cursor-help items-center"
              tabIndex={0}
              aria-describedby="gnn-skipped-tooltip"
            >
              <span className="rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 font-semibold text-amber-700">
                GNN: skipped
              </span>
              <div
                id="gnn-skipped-tooltip"
                role="tooltip"
                className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden w-56 -translate-x-1/2 rounded-lg bg-slate-800 p-2 text-center text-xs text-white shadow-lg group-hover:block group-focus-within:block"
              >
                GNN metrics require a synthetic ring holdout to calculate PR-AUC.
              </div>
            </div>
          ) : gnnStatus === "trained" && metrics?.gnn ? (
            <span className="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-slate-600">
              GNN: PR-AUC{" "}
              <span className="font-mono">{formatMetric(metrics.gnn.pr_auc)}</span>
              {" · "}P@10{" "}
              <span className="font-mono">{formatMetric(metrics.gnn.precision_at_10)}</span>
            </span>
          ) : (
            <span className="rounded-md border border-gray-200 bg-slate-100 px-2.5 py-1 text-slate-600">
              GNN: {gnnStatus ?? "unknown"}
            </span>
          )}

          {metrics?.note && (
            <span className="rounded-md border border-gray-200 bg-slate-50 px-2.5 py-1 font-mono text-xs text-slate-500">
              {metrics.note}
            </span>
          )}
        </div>

        {/* Flagged Rings Banner */}
        {data.rings && data.rings.length > 0 && (
          <div
            className={`mb-5 flex items-start gap-3 rounded-lg border p-4 text-sm ${
              isDanger
                ? "border-red-200 bg-red-50 text-red-700"
                : "border-amber-200 bg-amber-50 text-amber-700"
            }`}
          >
            <Info size={18} className="mt-0.5 shrink-0" />
            <div>
              <span className="font-semibold">Flagged Cartel Rings Detected: </span>
              {data.rings.map((r) => (
                <span key={r.ring_id} className="mr-2 my-0.5 inline-block rounded-md border border-gray-200 bg-white px-2 py-1 font-mono text-xs text-slate-700">
                  <strong>{r.ring_id}</strong>: [{r.vendor_ids.join(", ")}] — Link: {r.link_types.join("+")} (Collusion Score: {r.score.toFixed(2)})
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Selected Node Inspector Pill */}
        {selectedNodeInfo && (
          <div className="mb-4 flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            <div>
              <span className="mr-2 rounded-full bg-amber-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                Selected {selectedNodeInfo.type}
              </span>
              <span className="font-mono">{selectedNodeInfo.id}</span>: {selectedNodeInfo.label}
              {selectedNodeInfo.flagged && (
                <span
                  className={`ml-2 text-xs font-semibold ${
                    isDanger ? "text-red-700" : "text-amber-700"
                  }`}
                >
                  [Flagged Cartel Member]
                </span>
              )}
            </div>
            <button
              onClick={() => setSelectedNodeInfo(null)}
              className="cursor-pointer text-xs font-medium text-amber-700 underline"
            >
              Clear
            </button>
          </div>
        )}

        {/* Cytoscape Canvas Container */}
        <div
          ref={containerRef}
          role="region"
          aria-label="Interactive Cytoscape network graph"
          tabIndex={0}
          className="h-[550px] min-h-[550px] w-full rounded-xl border border-gray-200 bg-slate-50 shadow-inner focus:outline-hidden focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="mt-4 text-right">
        <span className="text-xs text-slate-500">
          Tip: Click any node to inspect details. Drag or scroll to pan/zoom.
        </span>
      </div>
    </div>
  );
}
