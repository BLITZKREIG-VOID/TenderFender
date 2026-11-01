import type { LlmModel } from "../api/client";
import { input, label } from "./styles";

interface Props {
  id: string;
  models: LlmModel[];
  value: string | null;
  onChange: (id: string) => void;
  freeFirst?: boolean;
  recommended?: string | null;
}

function optionText(m: LlmModel, recommended?: string | null): string {
  const ctx = m.context_length ? ` · ${Math.round(m.context_length / 1000)}k ctx` : "";
  return `${m.name || m.id}${ctx}${m.id === recommended ? " · recommended" : ""}`;
}

// Model dropdown grouped into free and paid models; free first when the key is a free OpenRouter key.
export default function ModelSelect({ id, models, value, onChange, freeFirst = true, recommended }: Props) {
  const free = models.filter((m) => m.free);
  const paid = models.filter((m) => !m.free);
  const groups = [
    { name: "Free models", items: free },
    { name: "Paid models (billed to your provider account)", items: paid },
  ];
  if (!freeFirst) groups.reverse();
  const known = value === null || models.some((m) => m.id === value);

  return (
    <div className="min-w-0 flex-1">
      <label htmlFor={id} className={label}>
        Model
      </label>
      <select
        id={id}
        className={input}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        data-testid={`${id}-select`}
      >
        {value === null && <option value="">Choose a model…</option>}
        {!known && value && <option value={value}>{value}</option>}
        {groups
          .filter((g) => g.items.length > 0)
          .map((g) => (
            <optgroup key={g.name} label={`${g.name} (${g.items.length})`}>
              {g.items.map((m) => (
                <option key={m.id} value={m.id}>
                  {optionText(m, recommended)}
                </option>
              ))}
            </optgroup>
          ))}
      </select>
    </div>
  );
}
