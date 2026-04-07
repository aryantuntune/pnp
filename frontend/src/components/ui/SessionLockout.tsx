"use client";

import { ShieldX } from "lucide-react";

interface SessionLockoutProps {
  redirectUrl: string;
}

export default function SessionLockout({ redirectUrl }: SessionLockoutProps) {
  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-sm rounded-xl border border-border bg-card p-8 text-center shadow-2xl">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
          <ShieldX className="h-7 w-7 text-red-600 dark:text-red-400" />
        </div>
        <h2 className="text-xl font-semibold text-foreground">Session Expired</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          You were logged out due to inactivity. Please log in again to continue.
        </p>
        <button
          onClick={() => { window.location.href = redirectUrl; }}
          className="mt-6 w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Log in again
        </button>
      </div>
    </div>
  );
}
