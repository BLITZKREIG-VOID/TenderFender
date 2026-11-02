import { Link } from "react-router-dom";
import { FolderPlus, FolderOpen, Key, ArrowRight, CheckCircle2, Sparkles } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import TenderList from "./TenderList";
import { panel, btnPrimary, btnSecondary } from "../components/styles";

export default function AppDashboard() {
  const { llm } = useAuth();

  const isLlmConfigured = Boolean(llm && llm.key && llm.key.trim() !== "");
  return (
    <div className="space-y-8">
      {/* Welcome & Dashboard Entry Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Entry to My Tenders */}
        <div className={`${panel} flex flex-col justify-between space-y-4`}>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="p-2.5 bg-blue-100 text-blue-900 rounded-lg border-2 border-black">
                <FolderOpen size={24} />
              </span>
              <span className="text-xs font-black uppercase tracking-wider bg-gray-100 border border-gray-300 px-2.5 py-1 rounded">
                Custom Documents
              </span>
            </div>
            <h2 className="text-xl font-black uppercase tracking-wide text-gray-950">
              My Tenders
            </h2>
            <p className="text-sm font-medium text-gray-700 leading-normal">
              Upload bid notices and RFP documents to verify qualification rules, check turnover requirements, and run integrity checks against guideline citations.
            </p>
          </div>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <Link
              to="/my-tenders"
              className={`${btnPrimary} min-h-[44px] text-xs`}
            >
              <FolderOpen size={16} />
              <span>Browse My Tenders</span>
            </Link>
            <Link
              to="/my-tenders/new"
              className={`${btnSecondary} min-h-[44px] text-xs`}
            >
              <FolderPlus size={16} />
              <span>Upload New</span>
            </Link>
          </div>
        </div>

        {/* AI Key Status Card */}
        <div className={`${panel} flex flex-col justify-between space-y-4`}>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="p-2.5 bg-purple-100 text-purple-900 rounded-lg border-2 border-black">
                <Key size={24} />
              </span>
              {isLlmConfigured ? (
                <span className="inline-flex items-center gap-1.5 text-xs font-black uppercase tracking-wider bg-emerald-100 text-emerald-900 border border-emerald-400 px-2.5 py-1 rounded">
                  <CheckCircle2 size={13} className="text-emerald-700" />
                  BYOK Active
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-xs font-black uppercase tracking-wider bg-blue-100 text-blue-900 border border-blue-400 px-2.5 py-1 rounded">
                  <Sparkles size={13} className="text-blue-700" />
                  Platform Default
                </span>
              )}
            </div>
            <h2 className="text-xl font-black uppercase tracking-wide text-gray-950">
              AI Key & Model Configuration
            </h2>
            <p className="text-sm font-medium text-gray-700 leading-normal">
              {isLlmConfigured
                ? `Custom API key connected (${llm?.model || "OpenRouter"}). Reasoning queries run via your direct key.`
                : "Using platform default AI engine for RAG reasoning and guideline citations. You can configure your own OpenRouter key in Settings."}
            </p>
          </div>

          <div className="pt-2">
            <Link
              to="/settings/ai"
              className={`${btnSecondary} min-h-[44px] text-xs`}
            >
              <span>Manage AI Settings</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </div>

      {/* Main Registry Section */}
      <div className="space-y-4">
        <TenderList />
      </div>
    </div>
  );
}
