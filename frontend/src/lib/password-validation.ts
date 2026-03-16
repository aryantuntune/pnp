/**
 * Shared password complexity validation matching backend rules.
 * Backend: backend/app/core/validators.py
 */

export interface PasswordCheck {
  valid: boolean;
  error: string;
}

export function validatePasswordComplexity(password: string): PasswordCheck {
  if (password.length < 8) {
    return { valid: false, error: "Password must be at least 8 characters" };
  }
  if (!/[A-Z]/.test(password)) {
    return { valid: false, error: "Password must contain at least one uppercase letter" };
  }
  if (!/[a-z]/.test(password)) {
    return { valid: false, error: "Password must contain at least one lowercase letter" };
  }
  if (!/\d/.test(password)) {
    return { valid: false, error: "Password must contain at least one digit" };
  }
  if (!/[^A-Za-z0-9]/.test(password)) {
    return { valid: false, error: "Password must contain at least one special character" };
  }
  return { valid: true, error: "" };
}
