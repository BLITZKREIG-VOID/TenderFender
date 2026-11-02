import { Check, Circle } from "lucide-react";
import { evaluatePasswordRules } from "../auth/passwordPolicy";

export function PasswordChecklist({ password }: { password: string }) {
  const rules = evaluatePasswordRules(password);

  return (
    <div
      className="p-3 bg-gray-50 border-2 border-gray-300 rounded-lg text-xs space-y-1.5"
      aria-label="Password requirements"
    >
      <span className="font-black uppercase tracking-wider text-gray-700 block mb-1">
        Password requirements:
      </span>
      {rules.map((rule) => (
        <div
          key={rule.id}
          className={`flex items-center gap-2 font-bold transition-colors ${
            rule.met ? "text-emerald-700" : "text-gray-500"
          }`}
        >
          {rule.met ? (
            <Check size={14} className="text-emerald-600 stroke-[3] shrink-0" aria-hidden="true" />
          ) : (
            <Circle size={12} className="text-gray-400 stroke-[2.5] shrink-0" aria-hidden="true" />
          )}
          <span>{rule.label}</span>
        </div>
      ))}
    </div>
  );
}
