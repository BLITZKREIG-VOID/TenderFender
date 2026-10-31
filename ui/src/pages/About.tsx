import { Scale, Network, ShieldCheck } from "lucide-react";

export default function About() {
  return (
    <div className="relative z-10 min-h-screen p-8 max-w-5xl mx-auto">
      {/* Hero Header */}
      <div className="bg-white/80 backdrop-blur-md border border-gray-200 shadow-sm rounded-2xl p-8 mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600 mb-4">
          The Mission
        </p>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 mb-6">
          Defending{" "}
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-cyan-500">
            Procurement Integrity
          </span>
        </h1>
      </div>

      {/* Mission Statement */}
      <div className="bg-white/80 backdrop-blur-md border border-gray-200 shadow-sm rounded-2xl p-8 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600">
            <Scale size={24} />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">Mission Statement</h2>
        </div>
        <p className="text-lg text-slate-600 leading-relaxed">
          Public procurement is vulnerable to sophisticated collusion and exclusionary drafting. The
          Tender Integrity Suite is an automated oversight platform designed to defend the integrity of
          high-value contracts. By fusing formal logic verification with network science, we empower
          auditors to instantly detect contradictory clauses, exclusionary requirements, and hidden
          vendor cartels before a tender is awarded.
        </p>
      </div>

      {/* Technology Stack */}
      <div className="bg-white/80 backdrop-blur-md border border-gray-200 shadow-sm rounded-2xl p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-cyan-100 text-cyan-600">
            <Network size={24} />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">Technology Stack</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Z3 Theorem Prover */}
          <div className="rounded-xl border border-gray-200 bg-slate-50 p-6">
            <div className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600 mb-4">
              <ShieldCheck size={22} />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-1">Z3 Theorem Prover</h3>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">
              Clause Formalization
            </p>
            <p className="text-sm text-slate-600 leading-relaxed">
              Powered by Microsoft&apos;s SMT (Satisfiability Modulo Theories) solver, our engine
              translates complex natural language requirements into strict mathematical constraints. It
              evaluates the entire ruleset simultaneously to prove whether a tender is legally
              satisfiable, instantly flagging contradictory eligibility criteria designed to lock out
              legitimate competitors.
            </p>
          </div>

          {/* Cytoscape.js & GNNs */}
          <div className="rounded-xl border border-gray-200 bg-slate-50 p-6">
            <div className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-cyan-100 text-cyan-600 mb-4">
              <Network size={22} />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-1">Cytoscape.js &amp; GNNs</h3>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">
              Network Analysis
            </p>
            <p className="text-sm text-slate-600 leading-relaxed">
              Collusion rarely happens in a vacuum. We utilize Cytoscape.js alongside graph neural
              network embeddings to visualize the hidden topology of procurement data. By mapping
              shared directors, overlapping addresses, and historical bidding patterns, the platform
              exposes synthetic cartel rings and highlights high-risk vendor pathways.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
