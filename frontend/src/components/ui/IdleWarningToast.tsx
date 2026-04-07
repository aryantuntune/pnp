"use client";

import { useEffect, useState } from "react";
import { Clock } from "lucide-react";

interface IdleWarningToastProps {
  remaining: number;   // ms remaining until lockout
  persistent: boolean; // true = stays visible (last 2 min), false = auto-dismiss
}

function formatCountdown(ms: number): string {
  const totalSec = Math.max(0, Math.ceil(ms / 1000));
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

export default function IdleWarningToast({
  remaining,
  persistent,
}: IdleWarningToastProps) {
  const [dismissed, setDismissed] = useState(false);

  // Auto-dismiss transient toasts after 5 seconds
  useEffect(() => {
    if (persistent) return;
    const timer = setTimeout(() => setDismissed(true), 5000);
    return () => clearTimeout(timer);
  }, [persistent]);

  if (dismissed && !persistent) return null;

  return (
    <div
      className={`fixed top-4 right-4 z-[100] max-w-sm animate-in slide-in-from-top-2 fade-in duration-300 ${
        persistent ? "" : "pointer-events-auto"
      }`}
    >
      <div
        className={`flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg ${
          persistent
            ? "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950"
            : "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950"
        }`}
      >
        <Clock
          className={`h-5 w-5 mt-0.5 shrink-0 ${
            persistent
              ? "text-red-600 dark:text-red-400"
              : "text-amber-600 dark:text-amber-400"
          }`}
        />
        <div className="flex-1 min-w-0">
          {persistent ? (
            <>
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                Session expiring in {formatCountdown(remaining)}
              </p>
              <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">
                Move your mouse or press a key to stay logged in.
              </p>
            </>
          ) : (
            <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
              Your session will expire soon due to inactivity.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
