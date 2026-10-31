import type { FusedData, Citation, Passage } from "../api/client";
import { FileText, Lightbulb, CheckSquare, Bookmark } from "lucide-react";

interface Props {
  fused: FusedData;
  passages: Passage[];
}

// "llm" and "cache" (a stored LLM answer) are AI-written; "template" is the deterministic writer.
function sourceLabel(source: string): string {
  if (source === "template") return "Template";
  if (source === "cache") return "Cached LLM";
  if (source === "llm") return "LLM";
  return source;
}

interface CitationDetails {
  title: string;
  section?: string;
  link?: string;
  tag: string;
  tagColor: string;
}

// Display metadata for a citation; guideline titles/links come from the passages the API read from kb/passages.
function getCitationDetails(cite: Citation, passages: Passage[]): CitationDetails {
  if (cite.kind === "guideline") {
    const passage = passages.find((p) => p.passage_id === cite.ref);
    const title = cite.source_title ?? (!passage?.missing ? passage?.source_title : undefined);
    const link = cite.source_url ?? (!passage?.missing ? passage?.source_url : undefined);
    if (!title) {
      return {
        title: `Guideline passage ${cite.ref} (text unavailable)`,
        tag: "Guideline",
        tagColor: "bg-blue-700 text-white",
      };
    }
    return {
      title,
      section: cite.section ?? passage?.section,
      link,
      tag: "Guideline",
      tagColor: "bg-blue-700 text-white",
    };
  }

  if (cite.kind === "finding") {
    return {
      title: `Rule Formalization Finding ${cite.ref} (Z3 Solver Core Constraint)`,
      tag: "Rule Finding",
      tagColor: "bg-red-700 text-white",
    };
  }

  if (cite.kind === "ring") {
    return {
      title: `Graph Analysis Flagged Ring ${cite.ref} (Collusion/Bidding Ring)`,
      tag: "Collusion Ring",
      tagColor: "bg-purple-700 text-white",
    };
  }

  return {
    title: `Reference ${cite.ref}`,
    tag: cite.kind,
    tagColor: "bg-gray-800 text-white",
  };
}

export default function DecisionPanel({ fused, passages }: Props) {
  return (
    <div className="bg-white rounded-xl shadow-md border-4 border-gray-900 p-6 text-black">
      <div className="flex items-center justify-between border-b-2 border-gray-300 pb-3 mb-6">
        <h2 className="text-xl font-black text-black flex items-center gap-2 uppercase tracking-wide">
          <FileText size={24} className="text-black" />
          Decision & Recommendation Panel
        </h2>
        {fused.decision_source && (
          <span className="text-xs font-mono font-bold px-2.5 py-1 bg-gray-200 text-gray-800 rounded border border-gray-400">
            Decision Source: {sourceLabel(fused.decision_source)} ({fused.decision_source})
          </span>
        )}
      </div>

      {/* 1. Reasoning Block */}
      <div className="mb-6">
        <h3 className="text-xs font-black text-gray-900 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <Lightbulb size={18} className="text-amber-600" />
          AI Synthesis & Audit Reasoning
        </h3>
        <div className="bg-gray-100 p-5 rounded-lg border-2 border-gray-400 text-base font-medium text-gray-950 leading-relaxed shadow-inner">
          {fused.reasoning}
        </div>
      </div>

      {/* 2. Citations as Referenced List */}
      <div className="mb-6">
        <h3 className="text-xs font-black text-gray-900 uppercase tracking-wider mb-3 flex items-center gap-1.5">
          <Bookmark size={18} className="text-blue-700" />
          Referenced Citations & Guidelines
        </h3>

        {fused.citations && fused.citations.length > 0 ? (
          <div className="bg-gray-50 border-2 border-gray-300 rounded-lg overflow-hidden divide-y divide-gray-300">
            {fused.citations.map((cite, i) => {
              const details = getCitationDetails(cite, passages ?? []);
              const isExternal = Boolean(details.link && details.link.startsWith("http"));

              return (
                <div
                  key={i}
                  className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span
                      className={`text-xs font-black px-2 py-0.5 rounded font-mono uppercase tracking-wider shrink-0 ${details.tagColor}`}
                    >
                      {details.tag}: {cite.ref}
                    </span>
                    {details.link ? (
                      <a
                        href={details.link}
                        target={isExternal ? "_blank" : undefined}
                        rel={isExternal ? "noreferrer" : undefined}
                        className="text-sm font-bold text-blue-800 hover:text-blue-950 hover:underline min-w-0 rounded focus:outline-hidden focus:ring-2 focus:ring-blue-600"
                      >
                        {details.title}
                        {details.section && (
                          <span className="font-semibold text-gray-700"> · {details.section}</span>
                        )}
                      </a>
                    ) : (
                      <span className="text-sm font-bold text-gray-950 min-w-0">
                        {details.title}
                        {details.section && (
                          <span className="font-semibold text-gray-700"> · {details.section}</span>
                        )}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-gray-600 italic">No citations recorded.</p>
        )}
      </div>

      {/* 3. Recommended Actions as Bulleted List */}
      <div>
        <h3 className="text-xs font-black text-gray-900 uppercase tracking-wider mb-3 flex items-center gap-1.5">
          <CheckSquare size={18} className="text-green-700" />
          Recommended Actions for Reviewer
        </h3>

        {fused.recommended_actions && fused.recommended_actions.length > 0 ? (
          <ul className="space-y-2.5 bg-gray-50 p-4 rounded-lg border-2 border-gray-300">
            {fused.recommended_actions.map((action, i) => (
              <li
                key={i}
                className="flex items-start gap-3 text-base text-gray-950 font-semibold"
              >
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-black text-white text-xs font-black shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span className="leading-normal">{action}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-600 italic">No explicit actions required.</p>
        )}
      </div>

      {/* 4. Mandatory Disclaimer (verbatim from FusedData.disclaimer) */}
      {fused.disclaimer && (
        <div className="mt-6 p-4 bg-gray-900 text-white rounded-lg border-2 border-black shadow-inner">
          <h3 className="text-xs font-black uppercase tracking-wider text-amber-300 mb-1">
            Disclaimer
          </h3>
          <p className="text-sm font-bold tracking-wide">{fused.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
