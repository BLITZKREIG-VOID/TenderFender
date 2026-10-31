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
      className="my-6 flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm"
    >
      <Loader2 className="mb-4 animate-spin text-slate-400" size={40} strokeWidth={2} />
      <h3 className="text-lg font-semibold text-slate-800">
        {message}
      </h3>
      <p className="mt-2 max-w-md text-sm text-slate-500">
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
    <div className="my-6 flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full border border-gray-200 bg-slate-100">
        <FolderSearch size={28} className="text-slate-500" />
      </div>
      <h3 className="text-lg font-semibold text-slate-800">
        {title}
      </h3>
      <p className="mt-2 max-w-md text-sm text-slate-500">
        {message}
      </p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-6 cursor-pointer rounded-lg bg-slate-800 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-slate-700 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
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
      className="my-6 rounded-xl border border-rose-200 bg-rose-50 p-6 text-slate-900 shadow-sm"
    >
      <div className="flex items-start gap-4">
        <div className="shrink-0 rounded-lg bg-rose-600 p-2 text-white">
          <AlertOctagon size={28} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-rose-600 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-white">
              Connection Failure
            </span>
          </div>
          <h3 className="mt-2 text-lg font-semibold text-rose-900">
            {title}
          </h3>
          <p className="mt-2 text-sm leading-relaxed text-rose-800">
            {error}
          </p>

          {import.meta.env.DEV ? (
            <div className="mt-4 rounded-lg border border-rose-200 bg-white p-3 font-mono text-sm text-slate-700">
              Ensure backend server is running:{" "}
              <span className="text-rose-700">MOCK=1 uvicorn api.main:app --reload</span>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-600">
              The service may be temporarily unavailable. Please retry in a moment.
            </p>
          )}

          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-5 inline-flex cursor-pointer items-center gap-2 rounded-lg bg-rose-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-rose-700 focus:outline-hidden focus:ring-2 focus:ring-rose-400"
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
