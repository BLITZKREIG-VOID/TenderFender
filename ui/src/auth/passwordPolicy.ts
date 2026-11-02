export interface PasswordRule {
  id: string;
  label: string;
  met: boolean;
}

export function evaluatePasswordRules(password: string): PasswordRule[] {
  return [
    { id: "length", label: "At least 10 characters", met: password.length >= 10 },
    { id: "uppercase", label: "At least one uppercase letter (A-Z)", met: /[A-Z]/.test(password) },
    { id: "lowercase", label: "At least one lowercase letter (a-z)", met: /[a-z]/.test(password) },
    { id: "number", label: "At least one number (0-9)", met: /[0-9]/.test(password) },
  ];
}

export function isPasswordPolicySatisfied(password: string): boolean {
  return evaluatePasswordRules(password).every((r) => r.met);
}

/**
 * Validates and sanitizes a return/redirect target to prevent open redirects.
 * Accepts only same-site relative paths starting with a single '/'.
 */
export function sanitizeNext(next: string | null | undefined, fallback = "/app"): string {
  if (!next) return fallback;
  const trimmed = next.trim();
  if (trimmed.startsWith("/") && !trimmed.startsWith("//") && !trimmed.includes("\\")) {
    return trimmed;
  }
  return fallback;
}
