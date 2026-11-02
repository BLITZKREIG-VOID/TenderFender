import { Link, Navigate } from "react-router-dom";
import { ArrowRight, CheckCircle2, ShieldCheck, Scale, FileText, Cpu, Eye } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { panel, btnPrimary, btnSecondary } from "../components/styles";

export default function Landing() {
  const { signedIn } = useAuth();

  if (signedIn) {
    return <Navigate to="/app" replace />;
  }

  return (
    <div className="space-y-16 py-4">
      {/* Hero Section */}
      <section className="text-center max-w-4xl mx-auto space-y-6 pt-4 sm:pt-8">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-100 border border-blue-300 text-blue-900 text-xs font-black uppercase tracking-wider">
          <ShieldCheck size={16} className="text-blue-700" />
          For procurement reviewers and auditors
        </div>

        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black text-gray-950 tracking-tight leading-tight">
          Spot risk indicators in public tenders before they become problems
        </h1>

        <p className="text-lg sm:text-xl font-medium text-gray-700 max-w-3xl mx-auto leading-relaxed">
          TenderFender checks public tender eligibility rules for risk indicators and explains them with cited Indian procurement guidelines.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Link
            to="/signup"
            className={`${btnPrimary} min-h-[44px] w-full sm:w-auto px-8 py-3 text-base`}
          >
            <span>Create account</span>
            <ArrowRight size={18} />
          </Link>
          <Link
            to="/login"
            className={`${btnSecondary} min-h-[44px] w-full sm:w-auto px-8 py-3 text-base`}
          >
            Sign in
          </Link>
        </div>

        <div className="pt-2">
          <Link
            to="/demo"
            className="inline-flex items-center gap-1.5 text-sm font-black text-blue-800 underline decoration-2 hover:text-blue-950 transition-colors py-2 px-3 rounded-md focus:outline-hidden focus:ring-4 focus:ring-blue-600 min-h-[44px]"
          >
            <Eye size={16} />
            <span>Preview the demo</span>
          </Link>
        </div>
      </section>

      {/* How It Works (3 Steps) */}
      <section className="max-w-6xl mx-auto space-y-8">
        <div className="text-center space-y-2">
          <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-wide text-gray-950">
            How It Works
          </h2>
          <p className="text-sm sm:text-base font-bold text-gray-600">
            Three rigorous stages from clause extraction to justified findings
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className={`${panel} flex flex-col justify-between space-y-4 relative overflow-hidden`}>
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-lg bg-blue-600 text-white font-black text-lg flex items-center justify-center border-2 border-black">
                1
              </div>
              <h3 className="text-lg font-black uppercase tracking-wide text-gray-950">
                Rule Solver Check
              </h3>
              <p className="text-sm font-medium text-gray-700 leading-normal">
                Eligibility rules are checked with a formal solver to determine boolean satisfiability, detecting restrictive or contradictory qualification barriers.
              </p>
            </div>
            <div className="pt-2 border-t border-gray-200 flex items-center gap-2 text-xs font-black text-blue-800 uppercase tracking-wider">
              <Cpu size={16} />
              <span>Z3 SMT Formalization</span>
            </div>
          </div>

          <div className={`${panel} flex flex-col justify-between space-y-4 relative overflow-hidden`}>
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-lg bg-blue-600 text-white font-black text-lg flex items-center justify-center border-2 border-black">
                2
              </div>
              <h3 className="text-lg font-black uppercase tracking-wide text-gray-950">
                Multi-Finding Fusion
              </h3>
              <p className="text-sm font-medium text-gray-700 leading-normal">
                Findings from network graphs, turnover thresholds, and bidding timelines are fused into one unified risk level with deterministic severity weights.
              </p>
            </div>
            <div className="pt-2 border-t border-gray-200 flex items-center gap-2 text-xs font-black text-blue-800 uppercase tracking-wider">
              <Scale size={16} />
              <span>Multi-Signal Fusion</span>
            </div>
          </div>

          <div className={`${panel} flex flex-col justify-between space-y-4 relative overflow-hidden`}>
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-lg bg-blue-600 text-white font-black text-lg flex items-center justify-center border-2 border-black">
                3
              </div>
              <h3 className="text-lg font-black uppercase tracking-wide text-gray-950">
                Guideline-Grounded Reasoning
              </h3>
              <p className="text-sm font-medium text-gray-700 leading-normal">
                An explanation cites guideline passages from GFR 2017, CVC Manuals, and relevant public procurement jurisprudence.
              </p>
            </div>
            <div className="pt-2 border-t border-gray-200 flex items-center gap-2 text-xs font-black text-blue-800 uppercase tracking-wider">
              <FileText size={16} />
              <span>GFR & CVC Knowledge Base</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3 Feature Cards */}
      <section className="max-w-6xl mx-auto space-y-8">
        <div className="text-center space-y-2">
          <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-wide text-gray-950">
            Platform Capabilities
          </h2>
          <p className="text-sm sm:text-base font-bold text-gray-600">
            Built for procurement authorities, oversight bodies, and vigilance professionals
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className={`${panel} space-y-3`}>
            <div className="p-3 bg-gray-100 rounded-lg w-fit border-2 border-black">
              <Cpu size={24} className="text-blue-700" />
            </div>
            <h3 className="text-lg font-black text-gray-950 uppercase tracking-wide">
              Automated Eligibility Validation
            </h3>
            <p className="text-sm font-medium text-gray-700 leading-relaxed">
              Verify clause conditions against turnover, prior experience, and joint venture parameters with verifiable logical proofs.
            </p>
            <ul className="space-y-1.5 pt-2 text-xs font-bold text-gray-800">
              <li className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-emerald-700" />
                <span>Deterministic SMT proofs</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-emerald-700" />
                <span>Zero hallucination constraint check</span>
              </li>
            </ul>
          </div>

          <div className={`${panel} space-y-3`}>
            <div className="p-3 bg-gray-100 rounded-lg w-fit border-2 border-black">
              <Scale size={24} className="text-blue-700" />
            </div>
            <h3 className="text-lg font-black text-gray-950 uppercase tracking-wide">
              Risk Indicator Scoring
            </h3>
            <p className="text-sm font-medium text-gray-700 leading-relaxed">
              Identify unusual patterns in bidder networks, short submission windows, and tailor-made criteria indicating tender manipulation risks.
            </p>
            <ul className="space-y-1.5 pt-2 text-xs font-bold text-gray-800">
              <li className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-emerald-700" />
                <span>Transparent scoring hierarchy</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-emerald-700" />
                <span>Clear escalate / review / clear verdicts</span>
              </li>
            </ul>
          </div>

          <div className={`${panel} space-y-3`}>
            <div className="p-3 bg-gray-100 rounded-lg w-fit border-2 border-black">
              <FileText size={24} className="text-blue-700" />
            </div>
            <h3 className="text-lg font-black text-gray-950 uppercase tracking-wide">
              Verifiable Legal Citations
            </h3>
            <p className="text-sm font-medium text-gray-700 leading-relaxed">
              Every finding maps directly to authoritative clauses in the General Financial Rules (GFR 2017) and Central Vigilance Commission guidelines.
            </p>
            <ul className="space-y-1.5 pt-2 text-xs font-bold text-gray-800">
              <li className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-emerald-700" />
                <span>Official chapter & rule references</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-emerald-700" />
                <span>Verifiable audit trail for vigilance</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Call to Action Bar */}
      <section className="max-w-4xl mx-auto">
        <div className="bg-black text-white rounded-xl border-4 border-gray-900 p-8 text-center space-y-5 shadow-xl">
          <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-tight text-white">
            Ready to Inspect Tender Integrity?
          </h2>
          <p className="text-gray-300 text-sm sm:text-base font-bold max-w-xl mx-auto">
            Create an account to analyze live procurement tenders, review vendor networks, and generate formal audit reports.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
            <Link
              to="/signup"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-black text-sm uppercase tracking-wider rounded-lg border-2 border-white shadow-md transition-all cursor-pointer min-h-[44px] w-full sm:w-auto"
            >
              <span>Create Account</span>
              <ArrowRight size={16} />
            </Link>
            <Link
              to="/demo"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-900 hover:bg-gray-800 text-white font-black text-sm uppercase tracking-wider rounded-lg border-2 border-gray-700 shadow-md transition-all cursor-pointer min-h-[44px] w-full sm:w-auto"
            >
              <span>Explore Demo Tenders</span>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
