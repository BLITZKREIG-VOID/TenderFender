import type { FusedData, Citation } from "../api/client";
import { FileText, Lightbulb, ExternalLink, CheckSquare, Bookmark } from "lucide-react";

interface Props {
  fused: FusedData;
}

// Helpers for citation display metadata
function getCitationDetails(cite: Citation) {
  if (cite.kind === "guideline") {
    // Official Procurement Guidelines / CVC Circulars / GFR mappings
    const guidelineTitles: Record<string, { title: string; link?: string }> = {
      "KB-001": {
        title: "General Financial Rules (GFR) 2017 – Rule 173 (Transparency & Fairness)",
        link: "https://doe.gov.in/order-rules/general-financial-rules-2017",
      },
      "KB-002": {
        title: "GFR 2017 – Rule 160 (Mandatory Wide Publicity & Transparency)",
        link: "https://doe.gov.in/order-rules/general-financial-rules-2017",
      },
      "KB-003": {
        title: "CVC Guidelines on Qualification Criteria – Office Order No. 12/04/04",
        link: "https://cvc.gov.in/",
      },
      "KB-004": {
        title: "CVC Circular 03/01/2012 – Restrictive & Tailored Eligibility Examination",
        link: "https://cvc.gov.in/",
      },
    };

    const info = guidelineTitles[cite.ref] || {
      title: `Procurement Guideline Standard (${cite.ref})`,
      link: "https://cvc.gov.in/",
    };

    return {
      title: info.title,
      link: info.link,
      tag: "Guideline",
      tagColor: "bg-blue-700 text-white",
    };
  }

  if (cite.kind === "finding") {
    return {
      title: `Rule Formalization Finding ${cite.ref} (Z3 Solver Core Constraint)`,
      link: `#finding-${cite.ref}`,
      tag: "Rule Finding",
      tagColor: "bg-red-700 text-white",
    };
  }

  if (cite.kind === "ring") {
    return {
      title: `Graph Analysis Flagged Ring ${cite.ref} (Collusion/Bidding Ring)`,
      link: `#ring-${cite.ref}`,
      tag: "Collusion Ring",
      tagColor: "bg-purple-700 text-white",
    };
  }

  return {
    title: `Reference ${cite.ref}`,
    link: "#",
    tag: cite.kind,
    tagColor: "bg-gray-800 text-white",
  };
}

export default function DecisionPanel({ fused }: Props) {
  return (
    <div className="bg-white rounded-xl shadow-md border-4 border-gray-900 p-6 text-black">
      <div className="flex items-center justify-between border-b-2 border-gray-300 pb-3 mb-6">
        <h2 className="text-xl font-black text-black flex items-center gap-2 uppercase tracking-wide">
          <FileText size={24} className="text-black" />
          Decision & Recommendation Panel
        </h2>
        {fused.decision_source && (
          <span className="text-xs font-mono font-bold px-2.5 py-1 bg-gray-200 text-gray-800 rounded border border-gray-400">
            Engine Source: {fused.decision_source.toUpperCase()}
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
              const details = getCitationDetails(cite);
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
                    <span className="text-sm font-bold text-gray-950 truncate">
                      {details.title}
                    </span>
                  </div>

                  {details.link && (
                    <a
                      href={details.link}
                      target={isExternal ? "_blank" : undefined}
                      rel={isExternal ? "noopener noreferrer" : undefined}
                      className="inline-flex items-center gap-1 text-xs font-black text-blue-800 hover:text-blue-950 hover:underline bg-blue-50 px-2.5 py-1 rounded border border-blue-300 shrink-0 self-start sm:self-auto"
                    >
                      <span>View Source</span>
                      <ExternalLink size={12} />
                    </a>
                  )}
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
    </div>
  );
}
