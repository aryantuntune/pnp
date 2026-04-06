"use client";

import { useState } from "react";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Clock } from "lucide-react";

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

  return (
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
  );
}
