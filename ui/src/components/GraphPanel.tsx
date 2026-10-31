import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import type { GraphResponse } from "../api/client";
import { Network, ZoomIn, ZoomOut, Maximize2, Info } from "lucide-react";

interface Props {
  data: GraphResponse | null;
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

export default function GraphPanel({ data }: Props) {
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
      <div className="bg-white rounded-xl shadow-md border-4 border-gray-900 p-6 flex flex-col justify-between">
        <div>
          <h2 className="text-xl font-black text-black mb-4 flex items-center gap-2 uppercase tracking-wide">
            <Network size={24} className="text-black" />
            Cartel & Collusion Network Graph
          </h2>
          <div className="p-8 text-center bg-gray-50 rounded-lg border-2 border-dashed border-gray-400">
            <p className="text-base font-bold text-gray-800">No graph entities recorded for this tender.</p>
          </div>
        </div>
      </div>
    );
  }

  const metrics = data.metrics;
  const gnnStatus = metrics?.gnn_status;
  const gnnSkipped = gnnStatus === "skipped";

  return (
    <div className="bg-white rounded-xl shadow-md border-4 border-gray-900 p-6 text-black flex flex-col justify-between">
      <div>
        {/* Header with Title and Graph Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-gray-300 pb-3 mb-4">
          <h2 className="text-xl font-black text-black flex items-center gap-2 uppercase tracking-wide">
            <Network size={24} className="text-black" />
            Cartel & Collusion Network Graph
          </h2>

          <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-lg border-2 border-black">
            <button
              onClick={handleZoomIn}
              aria-label="Zoom in graph"
              title="Zoom In"
              className="p-1.5 rounded hover:bg-white text-black font-black focus:outline-hidden focus:ring-2 focus:ring-blue-600 cursor-pointer"
            >
              <ZoomIn size={18} />
            </button>
            <button
              onClick={handleZoomOut}
              aria-label="Zoom out graph"
              title="Zoom Out"
              className="p-1.5 rounded hover:bg-white text-black font-black focus:outline-hidden focus:ring-2 focus:ring-blue-600 cursor-pointer"
            >
              <ZoomOut size={18} />
            </button>
            <button
              onClick={handleFit}
              aria-label="Reset zoom and fit all elements"
              title="Fit to Screen"
              className="p-1.5 rounded hover:bg-white text-black font-black focus:outline-hidden focus:ring-2 focus:ring-blue-600 cursor-pointer"
            >
              <Maximize2 size={18} />
            </button>
          </div>
        </div>

        {/* Large High-Contrast Legend */}
        <div className="p-3 bg-gray-100 rounded-lg border-2 border-black mb-4">
          <span className="text-xs font-black uppercase text-black block mb-2 tracking-wider">
            Display Legend & Node Classes:
          </span>
          <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm font-bold text-black">
            {Object.entries(NODE_COLORS).map(([type, cfg]) => (
              <span key={type} className="inline-flex items-center gap-1.5 bg-white px-2.5 py-1 rounded border border-gray-400">
                <span
                  className="w-4 h-4 rounded-full border-2 border-black inline-block shrink-0 shadow-2xs"
                  style={{ backgroundColor: cfg.bg }}
                />
                <span className="capitalize">{type}</span>
              </span>
            ))}
            <span className="inline-flex items-center gap-1.5 bg-white px-2.5 py-1 rounded border border-red-300">
              <span
                className="w-4 h-4 rounded-full border-2 border-black inline-block shrink-0 shadow-2xs"
                style={{ backgroundColor: FLAGGED_COLOR }}
              />
              <span className="text-red-950 font-black">Flagged Ring Entity</span>
            </span>
            <span className="inline-flex items-center gap-1.5 bg-red-100 px-2.5 py-1 rounded border-2 border-red-700">
              <span
                className="w-4 h-4 rounded-full border-2 border-red-950 inline-block shrink-0"
                style={{ backgroundColor: HIGHLIGHT_COLOR }}
              />
              <span className="text-red-950 font-black">Highlighted Cartel Path</span>
            </span>
          </div>
        </div>

        {/* Model Metrics & GNN Status */}
        <div className="mb-4 flex flex-wrap items-center gap-2 text-xs sm:text-sm font-bold">
          <span className="px-2.5 py-1 bg-black text-white rounded border-2 border-black uppercase tracking-wider">
            Model Metrics
          </span>

          {metrics?.baseline && (
            <span className="px-2.5 py-1 bg-white text-black rounded border border-gray-400">
              Baseline: PR-AUC{" "}
              <span className="font-mono">{formatMetric(metrics.baseline.pr_auc)}</span>
              {" · "}P@10{" "}
              <span className="font-mono">{formatMetric(metrics.baseline.precision_at_10)}</span>
            </span>
          )}

          {gnnSkipped ? (
            <span className="px-2.5 py-1 bg-amber-100 text-amber-950 rounded border-2 border-amber-600 font-black">
              GNN: skipped
            </span>
          ) : gnnStatus === "trained" && metrics?.gnn ? (
            <span className="px-2.5 py-1 bg-white text-black rounded border border-gray-400">
              GNN: PR-AUC{" "}
              <span className="font-mono">{formatMetric(metrics.gnn.pr_auc)}</span>
              {" · "}P@10{" "}
              <span className="font-mono">{formatMetric(metrics.gnn.precision_at_10)}</span>
            </span>
          ) : (
            <span className="px-2.5 py-1 bg-gray-200 text-gray-800 rounded border border-gray-400">
              GNN: {gnnStatus ?? "unknown"}
            </span>
          )}

          {metrics?.note && (
            <span className="px-2.5 py-1 bg-gray-100 text-gray-700 rounded border border-gray-300 font-mono text-xs">
              {metrics.note}
            </span>
          )}
        </div>

        {/* Flagged Rings Banner */}
        {data.rings && data.rings.length > 0 && (
          <div className="mb-4 p-3 bg-red-100 rounded-lg border-2 border-red-800 text-xs sm:text-sm text-red-950 font-bold flex items-start gap-2">
            <Info size={18} className="text-red-800 shrink-0 mt-0.5" />
            <div>
              <span className="font-black uppercase">Flagged Cartel Rings Detected: </span>
              {data.rings.map((r) => (
                <span key={r.ring_id} className="font-mono bg-white px-2 py-0.5 rounded border border-red-400 mr-2 inline-block my-0.5">
                  <strong>{r.ring_id}</strong>: [{r.vendor_ids.join(", ")}] — Link: {r.link_types.join("+")} (Collusion Score: {r.score.toFixed(2)})
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Selected Node Inspector Pill */}
        {selectedNodeInfo && (
          <div className="mb-3 p-3 bg-amber-50 rounded-lg border-2 border-amber-600 text-sm font-bold text-amber-950 flex items-center justify-between">
            <div>
              <span className="uppercase text-xs font-black bg-amber-600 text-white px-2 py-0.5 rounded mr-2">
                Selected {selectedNodeInfo.type}
              </span>
              <span className="font-mono">{selectedNodeInfo.id}</span>: {selectedNodeInfo.label}
              {selectedNodeInfo.flagged && (
                <span className="ml-2 text-xs font-black text-red-700 uppercase">[Flagged Cartel Member]</span>
              )}
            </div>
            <button
              onClick={() => setSelectedNodeInfo(null)}
              className="text-xs underline text-amber-900 cursor-pointer font-black"
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
          className="w-full min-h-[550px] h-[550px] border-4 border-gray-900 rounded-xl bg-gray-50 shadow-inner focus:outline-hidden focus:ring-4 focus:ring-blue-600"
        />
      </div>

      <div className="mt-3 text-right">
        <span className="text-xs font-bold text-gray-700">
          Tip: Click any node to inspect details. Drag or scroll to pan/zoom.
        </span>
      </div>
    </div>
  );
}
