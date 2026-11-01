import { useState, type FormEvent } from "react";
import { FolderSearch, Send, Loader2, User, Search } from "lucide-react";
import { api, apiError, describeError, type ChatMessage, type Citation, type Passage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getCitationDetails } from "./DecisionPanel";
import { useLlmGate, GatePrompt, BudgetNote } from "./LlmGate";
import CaseFile from "./CaseFile";
import { btnPrimary, errorBox, input } from "./styles";

// API contract: at most 10 messages, each <= 2000 chars, starting and ending with a user turn.
const MAX_MESSAGES = 9; // the largest odd count <= 10, so a trimmed history still starts with "user"
const MAX_CHARS = 2000;

interface Turn extends ChatMessage {
  citations?: Citation[];
}

export default function ChatPanel({ tenderId, passages }: { tenderId: string; passages: Passage[] }) {
  const { refreshMe } = useAuth();
  const gate = useLlmGate("chat");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = async (e: FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || !gate.llm?.model || busy) return;
    const next: Turn[] = [...turns, { role: "user", content: text }];
    setTurns(next);
    setDraft("");
    setBusy(true);
    setError(null);
    try {
      const messages: ChatMessage[] = next.slice(-MAX_MESSAGES).map(({ role, content }) => ({ role, content }));
      const r = await api.chat(tenderId, gate.llm.model, messages, {
        key: gate.llm.key,
        provider: gate.llm.provider ?? undefined,
      });
      setTurns([...next, { role: "assistant", content: r.data.answer, citations: r.data.citations }]);
    } catch (err) {
      setTurns(turns);
      setDraft(text);
      setError(describeError(apiError(err, "The investigator could not answer")));
    } finally {
      setBusy(false);
      void refreshMe();
    }
  };

  return (
    <CaseFile
      testId="chat-panel"
      fileNo="CHAT/BETA/2026-27"
      title="Ask the investigator"
      icon={<FolderSearch size={24} />}
      stampLabel="Beta feature: chat is still in development"
      status="Bids under technical evaluation — this assistant has not yet been awarded the contract."
      caveat="Our investigator is still gathering evidence. Answers may be wrong; verify against the cited clauses and passages."
    >
      {gate.status !== "ready" ? (
        <GatePrompt gate={gate} verb="chat about this tender's findings" />
      ) : (
        <div className="space-y-4">
          <BudgetNote gate={gate} action="chat" />

          <div aria-live="polite" className="space-y-3" data-testid="chat-transcript">
            {turns.length === 0 && (
              <p className="p-4 border-2 border-dashed border-gray-500 rounded-lg text-sm font-bold text-gray-800">
                Ask the investigator about this tender's findings, e.g. 'Why was CL5 flagged?'
              </p>
            )}
            {turns.map((t, i) => (
              <div
                key={i}
                className={`p-3.5 rounded-lg border-2 ${
                  t.role === "user" ? "bg-white border-gray-900 ml-8" : "bg-amber-50 border-amber-700 mr-8"
                }`}
              >
                <p className="text-xs font-black uppercase tracking-wider text-gray-800 flex items-center gap-1.5 mb-1">
                  {t.role === "user" ? <User size={14} /> : <Search size={14} />}
                  {t.role === "user" ? "You" : "Investigator (beta)"}
                </p>
                <p className="text-base font-medium text-gray-950 whitespace-pre-wrap leading-relaxed">{t.content}</p>
                {t.citations && t.citations.length > 0 && (
                  <ul className="mt-2 flex flex-wrap gap-2" aria-label="Cited references">
                    {t.citations.map((c, j) => {
                      const d = getCitationDetails(c, passages);
                      return (
                        <li key={j}>
                          <span
                            title={d.title}
                            className={`text-xs font-black px-2 py-0.5 rounded font-mono uppercase tracking-wider ${d.tagColor}`}
                          >
                            {d.tag}: {c.ref}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            ))}
            {busy && (
              <p role="status" className="text-sm font-bold text-gray-800 flex items-center gap-2">
                <Loader2 size={16} className="animate-spin" /> The investigator is reviewing the file
                {gate.isFree ? " (free models can be slow)" : ""}…
              </p>
            )}
          </div>

          {error && (
            <div role="alert" className={errorBox}>
              {error}
            </div>
          )}

          {gate.low ? (
            <p className="text-sm font-bold text-red-900" data-testid="chat-disabled-low">
              Chat is paused: today's request budget for this key or account is too low for another turn. It resets at
              the next UTC day.
            </p>
          ) : (
            <form onSubmit={(e) => void send(e)} className="space-y-2">
              <label htmlFor="chat-input" className="sr-only">
                Your question about this tender
              </label>
              <textarea
                id="chat-input"
                className={`${input} min-h-20`}
                value={draft}
                maxLength={MAX_CHARS}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Why was CL5 flagged?"
                disabled={busy}
              />
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-bold text-gray-700">
                  {draft.length}/{MAX_CHARS} · the last {MAX_MESSAGES} messages are sent as context
                </span>
                <button type="submit" className={btnPrimary} disabled={busy || !draft.trim()} data-testid="chat-send">
                  <Send size={16} /> Send
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </CaseFile>
  );
}
