import { useState, type FormEvent } from "react";
import { Loader2, Save } from "lucide-react";
import { api, apiError, describeError, type Profile, type ProfileInput } from "../api/client";
import {
  EXPERIENCE_OPTIONS,
  ORG_OPTIONS,
  PURPOSE_OPTIONS,
  ROLE_OPTIONS,
  STATE_OPTIONS,
} from "../auth/profileOptions";
import { btnPrimary, errorBox, input, label, noteBox } from "./styles";

type Draft = { [K in keyof Omit<ProfileInput, "consent">]: ProfileInput[K] | "" };

function OneTap<T extends string>({
  legend,
  name,
  options,
  value,
  onPick,
}: {
  legend: string;
  name: string;
  options: { value: T; label: string }[];
  value: T | "";
  onPick: (v: T) => void;
}) {
  return (
    <fieldset data-testid={`q-${name}`}>
      <legend className={label}>{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            aria-pressed={value === o.value}
            onClick={() => onPick(o.value)}
            className={`px-3 py-1.5 rounded-md text-sm font-black border-2 border-black cursor-pointer focus:outline-hidden focus:ring-4 focus:ring-blue-600 ${
              value === o.value ? "bg-black text-white" : "bg-white text-black hover:bg-gray-100"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

interface Props {
  initial: Profile | null;
  submitLabel: string;
  onSaved: (p: Profile) => void;
}

// Five one-tap questions + consent; used by onboarding and the profile page.
export default function ProfileForm({ initial, submitLabel, onSaved }: Props) {
  const [d, setD] = useState<Draft>({
    role: initial?.role ?? "",
    org_type: initial?.org_type ?? "",
    state: initial?.state ?? "",
    purpose: initial?.purpose ?? "",
    experience: initial?.experience ?? "",
  });
  const [consent, setConsent] = useState(Boolean(initial?.consent));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const complete = Boolean(d.role && d.org_type && d.state && d.purpose && d.experience && consent);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!d.role || !d.org_type || !d.state || !d.purpose || !d.experience || !consent) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.putProfile({
        role: d.role,
        org_type: d.org_type,
        state: d.state,
        purpose: d.purpose,
        experience: d.experience,
        consent: true,
      });
      onSaved(r.data);
    } catch (err) {
      setError(describeError(apiError(err, "Could not save your profile")));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={(e) => void submit(e)} className="space-y-5" data-testid="profile-form">
      <OneTap legend="1. Your role" name="role" options={ROLE_OPTIONS} value={d.role} onPick={(v) => setD({ ...d, role: v })} />
      <OneTap
        legend="2. Organisation type"
        name="org_type"
        options={ORG_OPTIONS}
        value={d.org_type}
        onPick={(v) => setD({ ...d, org_type: v })}
      />
      <div data-testid="q-state">
        <label htmlFor="profile-state" className={label}>
          3. State / UT
        </label>
        <select
          id="profile-state"
          className={`${input} max-w-md`}
          value={d.state}
          onChange={(e) => setD({ ...d, state: e.target.value })}
        >
          <option value="">Choose…</option>
          {STATE_OPTIONS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
      <OneTap
        legend="4. Main purpose"
        name="purpose"
        options={PURPOSE_OPTIONS}
        value={d.purpose}
        onPick={(v) => setD({ ...d, purpose: v })}
      />
      <OneTap
        legend="5. Procurement experience"
        name="experience"
        options={EXPERIENCE_OPTIONS}
        value={d.experience}
        onPick={(v) => setD({ ...d, experience: v })}
      />

      <div className={noteBox} data-testid="privacy-note">
        <p className="font-black uppercase tracking-wider text-xs mb-1">Privacy note</p>
        <p>
          We store your sign-in email and name, these five answers, daily usage counters (kept for 3 days), tenders you
          compile (up to 20) and your latest re-generation per tender. Your AI key is never stored on our servers: it
          stays in this browser and is sent only to our own API, in a request header. You can delete your account and
          all of this data from your profile page at any time.
        </p>
      </div>

      <label className="flex items-start gap-3 text-sm font-bold text-gray-950 cursor-pointer">
        <input
          type="checkbox"
          className="mt-0.5 w-5 h-5 accent-black"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          data-testid="consent"
        />
        I agree that TenderFender stores the data described above with my account.
      </label>

      {error && (
        <div role="alert" className={errorBox}>
          {error}
        </div>
      )}

      <button type="submit" className={btnPrimary} disabled={!complete || busy} data-testid="profile-submit">
        {busy ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} {submitLabel}
      </button>
    </form>
  );
}
