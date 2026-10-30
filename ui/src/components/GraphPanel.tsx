import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import type { GraphResponse } from "../api/client";
import { Network } from "lucide-react";

interface Props {
  data: GraphResponse | null;
}

const NODE_COLORS: Record<string, string> = {
  vendor: "#3b82f6",
  person: "#8b5cf6",
  address: "#f59e0b",
  buyer: "#10b981",
};

const FLAGGED_COLOR = "#ef4444";
const HIGHLIGHT_COLOR = "#dc2626";
const EDGE_COLOR = "#94a3b8";

export default function GraphPanel({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!data || !containerRef.current) return;

    // Build highlighted node/edge sets
    const highlightedNodes = new Set<string>();
    const highlightedEdges = new Set<string>();

    for (const path of data.highlighted_paths) {
      for (const nodeId of path.nodes) {
        highlightedNodes.add(nodeId);
      }
      // Mark edges between consecutive nodes in the path
      for (let i = 0; i < path.nodes.length - 1; i++) {
        highlightedEdges.add(`${path.nodes[i]}-${path.nodes[i + 1]}`);
        highlightedEdges.add(`${path.nodes[i + 1]}-${path.nodes[i]}`);
      }
    }

    const elements: cytoscape.ElementDefinition[] = [];

    // Nodes
    for (const node of data.graph.nodes) {
      const isHighlighted = highlightedNodes.has(node.id);
      elements.push({
        data: {
          id: node.id,
          label: `${node.id}\n${node.label}`,
          nodeType: node.type,
          flagged: node.flagged,
          highlighted: isHighlighted,
        },
      });
    }

    // Edges
    for (const edge of data.graph.edges) {
      const edgeKey1 = `${edge.source}-${edge.target}`;
      const edgeKey2 = `${edge.target}-${edge.source}`;
      const isHighlighted =
        highlightedEdges.has(edgeKey1) || highlightedEdges.has(edgeKey2);

      elements.push({
        data: {
          source: edge.source,
          target: edge.target,
          label: edge.type.replace("_", " "),
          highlighted: isHighlighted,
        },
      });
    }

    // Destroy previous instance
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-wrap": "wrap",
            "text-max-width": "100px",
            "font-size": "9px",
            "text-valign": "bottom",
            "text-margin-y": 4,
            width: 30,
            height: 30,
            "background-color": (ele: cytoscape.NodeSingular) => {
              if (ele.data("highlighted")) return HIGHLIGHT_COLOR;
              if (ele.data("flagged")) return FLAGGED_COLOR;
              return NODE_COLORS[ele.data("nodeType")] ?? "#6b7280";
            },
            "border-width": (ele: cytoscape.NodeSingular) =>
              ele.data("highlighted") ? 3 : ele.data("flagged") ? 2 : 0,
            "border-color": (ele: cytoscape.NodeSingular) =>
              ele.data("highlighted") ? "#991b1b" : FLAGGED_COLOR,
          },
        },
        {
          selector: "edge",
          style: {
            label: "data(label)",
            "font-size": "7px",
            "text-rotation": "autorotate",
            width: (ele: cytoscape.EdgeSingular) =>
              ele.data("highlighted") ? 3 : 1,
            "line-color": (ele: cytoscape.EdgeSingular) =>
              ele.data("highlighted") ? HIGHLIGHT_COLOR : EDGE_COLOR,
            "target-arrow-color": (ele: cytoscape.EdgeSingular) =>
              ele.data("highlighted") ? HIGHLIGHT_COLOR : EDGE_COLOR,
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
      ],
      layout: {
        name: "cose",
        animate: false,
        nodeRepulsion: () => 8000,
        idealEdgeLength: () => 100,
      },
    });

    return () => {
      cyRef.current?.destroy();
    };
  }, [data]);

  if (!data || data.graph.nodes.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Network size={20} /> Network Graph
        </h2>
        <p className="text-gray-500 text-sm">No graph data available.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <Network size={20} /> Network Graph
      </h2>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mb-3 text-xs">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <span key={type} className="flex items-center gap-1">
            <span
              className="w-3 h-3 rounded-full inline-block"
              style={{ backgroundColor: color }}
            />
            {type}
          </span>
        ))}
        <span className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded-full inline-block"
            style={{ backgroundColor: FLAGGED_COLOR }}
          />
          flagged
        </span>
        <span className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded-full inline-block border-2"
            style={{ backgroundColor: HIGHLIGHT_COLOR, borderColor: "#991b1b" }}
          />
          highlighted path
        </span>
      </div>

      {/* Rings info */}
      {data.rings.length > 0 && (
        <div className="mb-3 p-2 bg-red-50 rounded border border-red-200 text-xs text-red-700">
          Flagged rings:{" "}
          {data.rings.map((r) => (
            <span key={r.ring_id} className="font-mono mr-2">
              {r.ring_id} ({r.vendor_ids.join(", ")}, score:{" "}
              {r.score.toFixed(2)})
            </span>
          ))}
        </div>
      )}

      <div
        ref={containerRef}
        className="w-full border border-gray-100 rounded-lg bg-gray-50"
        style={{ height: 400 }}
      />
    </div>
  );
}

