import type { ReactNode } from "react";

interface Props {
  fileNo: string; // e.g. "CHAT/BETA/2026-27"
  title: string;
  icon: ReactNode;
  status: string; // the tender-notice "Status" row
  caveat: string;
  stampLabel: string; // accessible name of the CASE OPEN seal
  testId?: string;
  children: ReactNode;
}

// Beta treatment for unfinished features: an investigator's case-file folder with a "CASE OPEN" stamp.
// The joke is only ever about our own feature. Everything is real text; no images of text.
export default function CaseFile({ fileNo, title, icon, status, caveat, stampLabel, testId, children }: Props) {
  return (
    <section data-testid={testId} className="relative mt-8 rounded-xl border-4 border-gray-900 bg-white text-black shadow-md">
      <div className="absolute -top-[30px] left-6 px-4 py-1 bg-amber-200 border-4 border-b-0 border-gray-900 rounded-t-lg">
        <span className="font-mono text-xs font-black tracking-wider text-gray-950">FILE NO. {fileNo}</span>
      </div>

      <header className="relative bg-amber-100 border-b-4 border-gray-900 rounded-t-lg px-6 pt-5 pb-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-black uppercase tracking-widest text-gray-800">Investigation dossier</p>
            <h2 className="text-xl font-black text-black flex items-center gap-2 uppercase tracking-wide mt-0.5">
              {icon}
              {title}
            </h2>
          </div>
          <div
            role="note"
            aria-label={stampLabel}
            data-testid="case-open-stamp"
            className="-rotate-[8deg] select-none border-[5px] border-double border-red-800 rounded-md px-4 py-1.5 bg-amber-50 text-red-800 font-black text-2xl tracking-[0.25em] uppercase shadow-[inset_0_0_0_2px_rgba(153,27,27,0.35)]"
          >
            CASE OPEN
          </div>
        </div>

        <dl className="mt-4 grid grid-cols-[auto_1fr] border-2 border-gray-900 rounded-md overflow-hidden text-sm">
          <dt className="bg-gray-900 text-white font-black uppercase tracking-wider text-xs px-3 py-2 flex items-center">
            Status:
          </dt>
          <dd className="bg-white text-gray-950 font-bold px-3 py-2" data-testid="case-status">
            {status}
          </dd>
        </dl>
        <p className="mt-2 text-sm font-bold text-gray-950" data-testid="case-caveat">
          {caveat}
        </p>
      </header>

      <div className="p-6">{children}</div>
    </section>
  );
}
