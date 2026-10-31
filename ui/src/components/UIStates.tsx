import { AlertOctagon, RefreshCw, FolderSearch, Loader2 } from "lucide-react";

interface LoadingStateProps {
  message?: string;
  submessage?: string;
}

export function LoadingState({
  message = "Loading Tender Analysis...",
  submessage = "Fetching verified rules, graph networks, and fused decision data.",
}: LoadingStateProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col items-center justify-center p-12 bg-white rounded-xl border-4 border-gray-900 shadow-md text-center my-6"
    >
      <Loader2 className="animate-spin text-black mb-4" size={48} strokeWidth={2.5} />
      <h3 className="text-xl font-black text-black uppercase tracking-wide">
        {message}
      </h3>
      <p className="text-sm font-semibold text-gray-800 mt-2 max-w-md">
        {submessage}
      </p>
    </div>
  );
}

interface EmptyStateProps {
  title?: string;
  message?: string;
  actionText?: string;
  onAction?: () => void;
}

export function EmptyState({
  title = "No Tenders Available",
  message = "There are no tender artifacts or mock entries currently loaded in the system.",
  actionText,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12 bg-white rounded-xl border-4 border-gray-900 shadow-md text-center my-6">
      <div className="w-16 h-16 rounded-full bg-gray-100 border-2 border-black flex items-center justify-center mb-4">
        <FolderSearch size={32} className="text-black" />
      </div>
      <h3 className="text-2xl font-black text-black uppercase tracking-tight">
        {title}
      </h3>
      <p className="text-base font-semibold text-gray-800 mt-2 max-w-md">
        {message}
      </p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-6 px-5 py-2.5 bg-black text-white font-black text-sm uppercase tracking-wider rounded-lg border-2 border-black shadow-md hover:bg-gray-800 focus:outline-hidden focus:ring-4 focus:ring-blue-600 transition-all cursor-pointer"
        >
          {actionText}
        </button>
      )}
    </div>
  );
}

interface ErrorCardProps {
  title?: string;
  error?: string;
  onRetry?: () => void;
}

export function ErrorCard({
  title = "System Communication Error",
  error = "Failed to establish a connection with the Tender Integrity API server (http://localhost:8000).",
  onRetry,
}: ErrorCardProps) {
  return (
    <div
      role="alert"
      className="p-6 bg-red-50 border-4 border-red-700 rounded-xl shadow-lg my-6 text-black"
    >
      <div className="flex items-start gap-4">
        <div className="p-2 bg-red-700 text-white rounded-lg shrink-0 border-2 border-red-900">
          <AlertOctagon size={32} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-black uppercase tracking-widest px-2.5 py-0.5 bg-red-700 text-white rounded">
              Connection Failure
            </span>
          </div>
          <h3 className="text-2xl font-black text-red-950 mt-1 uppercase tracking-tight">
            {title}
          </h3>
          <p className="text-base font-bold text-red-900 mt-2 leading-relaxed">
            {error}
          </p>

          {import.meta.env.DEV ? (
            <div className="mt-4 p-3 bg-white/90 border-2 border-red-300 rounded-md text-sm font-bold text-gray-900 font-mono">
              Ensure backend server is running:{" "}
              <span className="text-red-700">MOCK=1 uvicorn api.main:app --reload</span>
            </div>
          ) : (
            <p className="mt-4 text-sm font-bold text-gray-900">
              The service may be temporarily unavailable. Please retry in a moment.
            </p>
          )}

          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 bg-red-700 hover:bg-red-800 text-white font-black text-sm uppercase tracking-wider rounded-lg border-2 border-red-950 shadow-md focus:outline-hidden focus:ring-4 focus:ring-red-500 transition-all cursor-pointer"
            >
              <RefreshCw size={16} />
              Retry Connection
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

