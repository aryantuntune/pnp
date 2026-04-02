import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Pre-April 2026 ticket data is hidden for non-SUPER_ADMIN users. */
export const DATA_CUTOFF_DATE = "2026-04-01";
