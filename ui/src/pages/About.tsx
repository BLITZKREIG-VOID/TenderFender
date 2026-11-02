import { Link } from "react-router-dom";
import { Scale, Network, ShieldCheck, FileText } from "lucide-react";
import { Beams } from "../components/ui/beams";
import { panel, link } from "../components/styles";

// About page (content from p4/app), restyled to the site's high-contrast panels.
// Wording follows the SoT rule: risk indicators for human review, never conclusions of wrongdoing.
export default function About() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="relative overflow-hidden rounded-xl border-4 border-gray-900 bg-gray-950 text-white shadow-md">
        <Beams className="absolute inset-0 opacity-60" />
        <div className="relative p-8 sm:p-10">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-blue-300 mb-3">The mission</p>
          <h1 className="text-3xl sm:text-5xl font-black tracking-tight">
            Defending procurement integrity
          </h1>
        </div>
      </div>

      <section className={panel}>
        <h2 className="text-xl font-black uppercase tracking-wide flex items-center gap-2 mb-3">
          <Scale size={24} /> Mission statement
        </h2>
        <p className="text-base sm:text-lg font-medium text-gray-900 leading-relaxed">
          Public procurement is vulnerable to collusion and to eligibility rules written so that only one bidder can
          qualify. TenderFender is an automated review aid for high-value contracts. It combines formal logic checks
          with vendor-network analysis so auditors can spot contradictory clauses, exclusionary requirements and
          suspicious vendor links early, then review each indicator against cited Indian procurement guidelines.
          Every result is a risk indicator for human review, not a finding of wrongdoing.
        </p>
      </section>

      <section className={panel}>
        <h2 className="text-xl font-black uppercase tracking-wide flex items-center gap-2 mb-5">
          <Network size={24} /> How it works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-lg border-2 border-gray-300 bg-gray-50 p-5">
            <ShieldCheck size={22} className="text-blue-700 mb-3" />
            <h3 className="text-base font-black">Z3 theorem prover</h3>
            <p className="text-xs font-black uppercase tracking-wider text-gray-600 mb-2">Clause formalization</p>
            <p className="text-sm font-medium text-gray-900 leading-relaxed">
              Eligibility clauses are translated into formal constraints, which an auditor confirms. Microsoft&apos;s Z3
              solver then checks the whole rule set at once: it proves when clauses contradict each other, or when
              exactly one registered vendor can qualify.
            </p>
          </div>
          <div className="rounded-lg border-2 border-gray-300 bg-gray-50 p-5">
            <Network size={22} className="text-blue-700 mb-3" />
            <h3 className="text-base font-black">Vendor network graph</h3>
            <p className="text-xs font-black uppercase tracking-wider text-gray-600 mb-2">Network analysis</p>
            <p className="text-sm font-medium text-gray-900 leading-relaxed">
              Shared directors, shared addresses and bidding patterns are mapped as a graph (shown with Cytoscape.js)
              to flag possible bid rings. A graph neural network is an experimental second opinion; the demo
              network data is synthetic.
            </p>
          </div>
          <div className="rounded-lg border-2 border-gray-300 bg-gray-50 p-5">
            <FileText size={22} className="text-blue-700 mb-3" />
            <h3 className="text-base font-black">Cited recommendation</h3>
            <p className="text-xs font-black uppercase tracking-wider text-gray-600 mb-2">Decision layer</p>
            <p className="text-sm font-medium text-gray-900 leading-relaxed">
              A fixed rule turns the findings into a risk level and a recommendation: clear, review or escalate.
              The written reasoning cites the matching guideline passages, and every citation is checked against a
              real source.
            </p>
          </div>
        </div>
      </section>

      <p className="text-sm font-bold text-gray-800">
        See it on the demo tenders: <Link to="/demo" className={link}>Preview the demo</Link>
      </p>
    </div>
  );
}
