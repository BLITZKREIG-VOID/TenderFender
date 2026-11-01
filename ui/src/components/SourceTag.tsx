import type { TenderSource } from "../api/client";

export const sourceLabel = (source: TenderSource): string =>
  source === "real" ? "Real tender" : "Synthetic demo";

export default function SourceTag({ source }: { source: TenderSource }) {
  const real = source === "real";
  return (
    <span
      data-testid="source-tag"
      className={`inline-block px-2.5 py-0.5 rounded-md text-xs font-black uppercase tracking-wider border-2 ${
        real ? "bg-blue-800 text-white border-blue-950" : "bg-white text-gray-900 border-gray-700"
      }`}
    >
      {sourceLabel(source)}
    </span>
  );
}
