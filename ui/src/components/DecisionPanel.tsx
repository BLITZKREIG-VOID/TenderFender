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
function getCitationDetails(cite: Citation, passages: Passage[], isDanger: boolean): CitationDetails {
  if (cite.kind === "guideline") {
    const passage = passages.find((p) => p.passage_id === cite.ref);
    const title = cite.source_title ?? (!passage?.missing ? passage?.source_title : undefined);
    const link = cite.source_url ?? (!passage?.missing ? passage?.source_url : undefined);
    if (!title) {
      return {
        title: `Guideline passage ${cite.ref} (text unavailable)`,
        tag: "Guideline",
        tagColor: "border-blue-200 bg-blue-50 text-blue-700",
      };
    }
    return {
      title,
      section: cite.section ?? passage?.section,
      link,
      tag: "Guideline",
      tagColor: "border-blue-200 bg-blue-50 text-blue-700",
    };
  }

  if (cite.kind === "finding") {
    return {
      title: `Rule Formalization Finding ${cite.ref} (Z3 Solver Core Constraint)`,
      tag: "Rule Finding",
      // Red is reserved for high-risk / escalate tenders; other findings are amber.
      tagColor: isDanger
        ? "border-red-200 bg-red-50 text-red-700"
        : "border-amber-200 bg-amber-50 text-amber-700",
    };
  }

  if (cite.kind === "ring") {
    return {
      title: `Graph Analysis Flagged Ring ${cite.ref} (Collusion/Bidding Ring)`,
      tag: "Collusion Ring",
      tagColor: "border-purple-200 bg-purple-50 text-purple-700",
    };
  }

  return {
    title: `Reference ${cite.ref}`,
    tag: cite.kind,
    tagColor: "border-gray-200 bg-slate-100 text-slate-600",
  };
}

export default function DecisionPanel({ fused, passages }: Props) {
  const isDanger =
    fused.decision?.toLowerCase() === "escalate" ||
    fused.risk_level?.toLowerCase() === "high";

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 text-slate-900 shadow-sm">
      <div className="mb-6 flex items-center justify-between gap-4 border-b border-gray-200 pb-4">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-800">
          <FileText size={20} className="text-slate-500" />
          Decision & Recommendation Panel
        </h2>
        {fused.decision_source && (
          <span className="rounded-md border border-gray-200 bg-slate-100 px-2.5 py-1 font-mono text-xs font-medium text-slate-600">
            Decision Source: {sourceLabel(fused.decision_source)} ({fused.decision_source})
          </span>
        )}
      </div>

      {/* 1. Reasoning Block */}
      <div className="mb-6">
        <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700">
          <Lightbulb size={16} className="text-amber-500" />
          AI Synthesis & Audit Reasoning
        </h3>
        <div className="rounded-lg border border-gray-200 bg-slate-50 p-5 text-base leading-relaxed text-slate-700">
          {fused.reasoning}
        </div>
      </div>

      {/* 2. Citations as Referenced List */}
      <div className="mb-6">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
          <Bookmark size={16} className="text-blue-600" />
          Referenced Citations & Guidelines
        </h3>

        {fused.citations && fused.citations.length > 0 ? (
          <div className="overflow-hidden divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
            {fused.citations.map((cite, i) => {
              const details = getCitationDetails(cite, passages ?? [], isDanger);
              const isExternal = Boolean(details.link && details.link.startsWith("http"));

              return (
                <div
                  key={i}
                  className="flex flex-col justify-between gap-2 p-4 transition-colors hover:bg-slate-50 sm:flex-row sm:items-center"
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span
                      className={`shrink-0 rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wide ${details.tagColor}`}
                    >
                      {details.tag}: {cite.ref}
                    </span>
                    {details.link ? (
                      <a
                        href={details.link}
                        target={isExternal ? "_blank" : undefined}
                        rel={isExternal ? "noreferrer" : undefined}
                        className="min-w-0 rounded text-sm font-medium text-blue-700 hover:text-blue-800 hover:underline focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                      >
                        {details.title}
                        {details.section && (
                          <span className="font-normal text-slate-500"> · {details.section}</span>
                        )}
                      </a>
                    ) : (
                      <span className="min-w-0 text-sm font-medium text-slate-700">
                        {details.title}
                        {details.section && (
                          <span className="font-normal text-slate-500"> · {details.section}</span>
                        )}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm italic text-slate-500">No citations recorded.</p>
        )}
      </div>

      {/* 3. Recommended Actions as Bulleted List */}
      <div>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
          <CheckSquare size={16} className="text-green-600" />
          Recommended Actions for Reviewer
        </h3>

        {fused.recommended_actions && fused.recommended_actions.length > 0 ? (
          <ul className="space-y-3 rounded-lg border border-gray-200 bg-slate-50 p-4">
            {fused.recommended_actions.map((action, i) => (
              <li
                key={i}
                className="flex items-start gap-3 text-base font-medium text-slate-700"
              >
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-white">
                  {i + 1}
                </span>
                <span className="leading-normal">{action}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm italic text-slate-500">No explicit actions required.</p>
        )}
      </div>

      {/* 4. Mandatory Disclaimer (verbatim from FusedData.disclaimer) */}
      {fused.disclaimer && (
        <div className="mt-6 rounded-lg border border-amber-200 bg-slate-800 p-4 text-amber-400 font-medium shadow-inner">
          <p className="text-sm text-amber-300 leading-relaxed">{fused.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
