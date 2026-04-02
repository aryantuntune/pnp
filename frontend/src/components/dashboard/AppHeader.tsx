"use client";

import { useState, useEffect, useRef } from "react";
import { Bell, Menu, Moon, Sun, RefreshCw } from "lucide-react";
import { User } from "@/types";
import { useTheme } from "@/components/ThemeProvider";
import { Button } from "@/components/ui/button";
import useVersionCheck from "@/hooks/useVersionCheck";

interface AppHeaderProps {
  user: User;
  onMobileMenuToggle: () => void;
}

export default function AppHeader({ onMobileMenuToggle }: AppHeaderProps) {
  const { mode, toggleMode } = useTheme();
  const { hasUpdate, reload } = useVersionCheck();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Auto-open dropdown when a new update is detected
  useEffect(() => {
    if (hasUpdate) setDropdownOpen(true);
  }, [hasUpdate]);

  // Close dropdown on outside click
  useEffect(() => {
    if (!dropdownOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [dropdownOpen]);

  return (
    <header className="h-14 border-b border-border bg-card flex items-center justify-between px-4 lg:px-6">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 lg:hidden"
          onClick={onMobileMenuToggle}
        >
          <Menu className="h-5 w-5" />
        </Button>
      </div>
      <div className="flex items-center gap-2 lg:gap-3">
        <Button variant="ghost" size="icon" className="h-9 w-9" onClick={toggleMode}>
          {mode === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        {/* Notification bell */}
        <div className="relative" ref={dropdownRef}>
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 relative"
            onClick={() => setDropdownOpen((prev) => !prev)}
          >
            <Bell className="h-4 w-4" />
            {hasUpdate && (
              <span className="absolute top-1.5 right-1.5 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-card animate-pulse" />
            )}
          </Button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-80 rounded-xl border border-border bg-card shadow-xl z-50">
              <div className="px-4 py-3 border-b border-border">
                <p className="text-sm font-semibold text-foreground">Notifications</p>
              </div>
              <div className="p-4">
                {hasUpdate ? (
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
                      <RefreshCw className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground">New update available</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        A new version has been deployed. Please reload to get the latest changes.
                      </p>
                      <Button
                        size="sm"
                        className="mt-2.5 h-8 text-xs"
                        onClick={reload}
                      >
                        <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                        Reload now
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-2">
                    No new notifications
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
