"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Route } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Clock, Ship } from "lucide-react";

interface OperationsTabProps {
  timeLockEnabled: boolean;
  onTimeLockChange: (enabled: boolean) => void;
}

export default function OperationsTab({
  timeLockEnabled,
  onTimeLockChange,
}: OperationsTabProps) {
  const [toggling, setToggling] = useState(false);
  const [error, setError] = useState("");

  // Route multi-ticketing state
  const [routes, setRoutes] = useState<Route[]>([]);
  const [routesLoading, setRoutesLoading] = useState(true);
  const [togglingRouteId, setTogglingRouteId] = useState<number | null>(null);
  const [routeError, setRouteError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<Route[]>("/api/routes?limit=100&status=active");
        setRoutes(data);
      } catch {
        setRouteError("Failed to load routes.");
      } finally {
        setRoutesLoading(false);
      }
    })();
  }, []);

  const handleToggle = async (checked: boolean) => {
    setError("");
    setToggling(true);
    try {
      const { data } = await api.put<{ time_lock_enabled: boolean }>(
        "/api/settings/time-lock",
        { enabled: checked },
      );
      onTimeLockChange(data.time_lock_enabled);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "Failed to update time-lock setting.";
      setError(msg);
    } finally {
      setToggling(false);
    }
  };

  const handleRouteToggle = async (routeId: number, checked: boolean) => {
    setRouteError("");
    setTogglingRouteId(routeId);
    try {
      const { data } = await api.patch<Route>(`/api/routes/${routeId}`, {
        multi_ticketing_enabled: checked,
      });
      setRoutes((prev) =>
        prev.map((r) => (r.id === routeId ? { ...r, multi_ticketing_enabled: data.multi_ticketing_enabled } : r))
      );
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "Failed to update route setting.";
      setRouteError(msg);
    } finally {
      setTogglingRouteId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Time-Lock Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Clock className="h-5 w-5" />
            Ticketing Operations
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-1">
              <Label htmlFor="time-lock-toggle" className="text-sm font-medium">
                Ferry Schedule Time-Lock
              </Label>
              <p className="text-xs text-muted-foreground leading-relaxed max-w-md">
                When enabled, normal ticketing is locked outside ferry hours (opens
                45 min before first ferry, closes 30 min after last ferry).
                Multi-ticketing is locked during ferry hours. Turn off to allow
                both screens at all times.
              </p>
            </div>
            <Switch
              id="time-lock-toggle"
              checked={timeLockEnabled}
              onCheckedChange={handleToggle}
              disabled={toggling}
            />
          </div>

          {error && (
            <p className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded p-2">
              {error}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Route Multi-Ticketing Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Ship className="h-5 w-5" />
            Multi-Ticketing per Route
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground leading-relaxed">
            Enable or disable multi-ticketing for each route. Routes with multi-ticketing
            disabled will only use normal ticketing (operators can extend their schedule timing).
          </p>

          {routesLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full rounded-lg" />
              ))}
            </div>
          ) : routes.length === 0 ? (
            <p className="text-sm text-muted-foreground">No active routes found.</p>
          ) : (
            <div className="space-y-3">
              {routes.map((route) => (
                <div
                  key={route.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div className="space-y-1">
                    <Label
                      htmlFor={`route-mt-${route.id}`}
                      className="text-sm font-medium"
                    >
                      {route.branch_one_name} &harr; {route.branch_two_name}
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      Route #{route.id}
                    </p>
                  </div>
                  <Switch
                    id={`route-mt-${route.id}`}
                    checked={route.multi_ticketing_enabled}
                    onCheckedChange={(checked) =>
                      handleRouteToggle(route.id, checked)
                    }
                    disabled={togglingRouteId === route.id}
                  />
                </div>
              ))}
            </div>
          )}

          {routeError && (
            <p className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded p-2">
              {routeError}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
