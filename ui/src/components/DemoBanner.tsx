import { Link } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";

export function DemoBanner() {
  return (
    <div
      className="bg-blue-900 text-white border-4 border-blue-950 rounded-xl p-4 sm:p-5 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-md"
      role="region"
      aria-label="Demo preview banner"
    >
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-800 rounded-lg border-2 border-blue-400 shrink-0">
          <Sparkles size={22} className="text-yellow-300" />
        </div>
        <div>
          <span className="text-sm sm:text-base font-black uppercase tracking-wide block text-white">
            Demo preview: synthetic data. Create an account to see real tenders.
          </span>
          <span className="text-xs sm:text-sm font-semibold text-blue-200">
            Previewing synthetic test cases (T-001, T-002, T-003) in read-only mode without AI panels.
          </span>
        </div>
      </div>
      <Link
        to="/signup"
        className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-yellow-400 hover:bg-yellow-300 text-black font-black text-xs uppercase tracking-wider rounded-lg border-2 border-black shadow-md transition-all shrink-0 min-h-[44px]"
      >
        <span>Create account</span>
        <ArrowRight size={16} />
      </Link>
    </div>
  );
}
