import type { Experience, OrgType, Purpose, Role } from "../api/client";

// Values are the API enums verbatim (PUT /api/me/profile rejects anything else).
export const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "procurement_officer", label: "Procurement officer" },
  { value: "auditor_vigilance", label: "Auditor / vigilance" },
  { value: "journalist", label: "Journalist" },
  { value: "researcher_student", label: "Researcher / student" },
  { value: "vendor_contractor", label: "Vendor / contractor" },
  { value: "citizen", label: "Citizen" },
  { value: "other", label: "Other" },
];

export const ORG_OPTIONS: { value: OrgType; label: string }[] = [
  { value: "central_govt", label: "Central government" },
  { value: "state_govt", label: "State government" },
  { value: "psu", label: "PSU" },
  { value: "private", label: "Private company" },
  { value: "ngo_media", label: "NGO / media" },
  { value: "academic", label: "Academic" },
  { value: "individual", label: "Individual" },
];

export const PURPOSE_OPTIONS: { value: Purpose; label: string }[] = [
  { value: "check_my_tenders", label: "Check my tenders" },
  { value: "audit_oversight", label: "Audit / oversight" },
  { value: "research", label: "Research" },
  { value: "learning", label: "Learning" },
  { value: "other", label: "Other" },
];

export const EXPERIENCE_OPTIONS: { value: Experience; label: string }[] = [
  { value: "new", label: "New to procurement" },
  { value: "some", label: "Some experience" },
  { value: "expert", label: "Expert" },
];

// 28 states and 8 union territories (official names, exact-match on the server), plus outside_india.
export const STATE_OPTIONS: { value: string; label: string }[] = [
  ...[
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
  ].map((s) => ({ value: s, label: s })),
  { value: "outside_india", label: "Outside India" },
];

export function labelFor(options: { value: string; label: string }[], value: string | undefined): string {
  return options.find((o) => o.value === value)?.label ?? value ?? "—";
}
