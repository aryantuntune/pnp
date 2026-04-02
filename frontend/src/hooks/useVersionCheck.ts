import { useState, useEffect, useRef, useCallback } from "react";
import api from "@/lib/api";

const POLL_INTERVAL = 60 * 1000; // 60 seconds
const STORAGE_KEY = "ssmspl_build_id";

export default function useVersionCheck() {
  const initialBuildId = useRef<string | null>(null);
  const [hasUpdate, setHasUpdate] = useState(false);

  const check = useCallback(async () => {
    try {
      const res = await api.get("/api/version");
      const serverBuildId: string = res.data.build_id;

      if (initialBuildId.current === null) {
        // First check after page load
        initialBuildId.current = serverBuildId;

        // Compare against persisted build ID from previous session
        // to detect stale-cache loads (user opens browser after deploy)
        try {
          const stored = localStorage.getItem(STORAGE_KEY);
          if (stored && stored !== serverBuildId) {
            // Page JS is from an older build — notify user
            setHasUpdate(true);
            return;
          }
        } catch {
          // localStorage unavailable (private browsing) — skip
        }

        // Page is current — persist build ID for future sessions
        try {
          localStorage.setItem(STORAGE_KEY, serverBuildId);
        } catch {}
      } else if (serverBuildId !== initialBuildId.current) {
        // Server restarted/deployed while page was open
        setHasUpdate(true);
      }
    } catch {
      // Network error or server down — retry next poll
    }
  }, []);

  useEffect(() => {
    check();
    const id = setInterval(check, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [check]);

  const reload = useCallback(async () => {
    // Clear persisted build ID so the reloaded page starts fresh
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}

    // Unregister service workers to prevent stale cached asset serving
    if ("serviceWorker" in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map((r) => r.unregister()));
    }

    // Clear all SW-managed caches
    if ("caches" in window) {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    }

    // Full reload from server
    window.location.reload();
  }, []);

  return { hasUpdate, reload };
}
