"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import api from "@/lib/api";

const IDLE_LIMIT = 10 * 60 * 1000;        // 10 minutes
const WARN_5MIN  = 5 * 60 * 1000;         // 5 minutes remaining
const WARN_2MIN  = 2 * 60 * 1000;         // 2 minutes remaining
const HEARTBEAT_INTERVAL = 3 * 60 * 1000; // 3 minutes
const TICK_INTERVAL = 1000;                // 1 second

interface IdleWarning {
  remaining: number;   // ms remaining
  persistent: boolean; // true when <=2min (stays visible)
}

interface UseIdleTimeoutReturn {
  isLockedOut: boolean;
  warning: IdleWarning | null;
}

interface UseIdleTimeoutOptions {
  logoutFn: () => Promise<void>;
  heartbeatUrl?: string; // defaults to "/api/auth/me"
}

export function useIdleTimeout({
  logoutFn,
  heartbeatUrl = "/api/auth/me",
}: UseIdleTimeoutOptions): UseIdleTimeoutReturn {
  const [isLockedOut, setIsLockedOut] = useState(false);
  const [warning, setWarning] = useState<IdleWarning | null>(null);

  const lastActiveAtRef = useRef(0);
  const lastHeartbeatRef = useRef(0);
  const wasActiveSinceHeartbeatRef = useRef(false);
  const shown5minRef = useRef(false);
  const lockedOutRef = useRef(false);
  const initializedRef = useRef(false);

  const resetActivity = useCallback(() => {
    if (lockedOutRef.current) return; // ignore activity after lockout
    lastActiveAtRef.current = Date.now();
    wasActiveSinceHeartbeatRef.current = true;
    shown5minRef.current = false;
    setWarning(null);
  }, []);

  // Initialize timestamp refs on mount (avoids calling Date.now() during render)
  useEffect(() => {
    const now = Date.now();
    lastActiveAtRef.current = now;
    lastHeartbeatRef.current = now;
    initializedRef.current = true;
  }, []);

  const triggerLockout = useCallback(() => {
    if (lockedOutRef.current) return;
    lockedOutRef.current = true;
    setIsLockedOut(true);
    setWarning(null);
    // Fire-and-forget logout to clean up server session
    logoutFn().catch(() => {});
  }, [logoutFn]);

  // 1-second tick: compute elapsed, drive warnings/lockout, send heartbeat
  useEffect(() => {
    const tick = () => {
      if (lockedOutRef.current || !initializedRef.current) return;

      const now = Date.now();
      const elapsed = now - lastActiveAtRef.current;
      const remaining = IDLE_LIMIT - elapsed;

      if (remaining <= 0) {
        triggerLockout();
        return;
      }

      if (remaining <= WARN_2MIN) {
        setWarning({ remaining, persistent: true });
      } else if (remaining <= WARN_5MIN && !shown5minRef.current) {
        shown5minRef.current = true;
        setWarning({ remaining, persistent: false });
      }

      // Heartbeat: send if user was active and enough time passed
      if (
        wasActiveSinceHeartbeatRef.current &&
        now - lastHeartbeatRef.current >= HEARTBEAT_INTERVAL
      ) {
        wasActiveSinceHeartbeatRef.current = false;
        lastHeartbeatRef.current = now;
        api.get(heartbeatUrl).catch(() => {
          // 401 handled by axios interceptor
        });
      }
    };

    const intervalId = setInterval(tick, TICK_INTERVAL);
    return () => clearInterval(intervalId);
  }, [triggerLockout, heartbeatUrl]);

  // Activity event listeners
  useEffect(() => {
    const events = ["mousedown", "keydown", "touchstart", "scroll"];
    events.forEach((e) => window.addEventListener(e, resetActivity));
    return () => {
      events.forEach((e) => window.removeEventListener(e, resetActivity));
    };
  }, [resetActivity]);

  // Visibility change: immediate check on device wake / tab switch
  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState !== "visible") return;
      if (lockedOutRef.current || !initializedRef.current) return;

      const elapsed = Date.now() - lastActiveAtRef.current;
      if (elapsed >= IDLE_LIMIT) {
        triggerLockout();
      }
    };

    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [triggerLockout]);

  return { isLockedOut, warning };
}
