"use client";

import { useState } from "react";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useTheme } from "@/components/ThemeProvider";
import { DEFAULT_THEMES } from "@/lib/themes";
import { Palette } from "lucide-react";

export default function AppearanceTab() {
  const { theme, mode, setThemeName, toggleMode } = useTheme();
  const [themeSubmitting, setThemeSubmitting] = useState(false);
  const [themeSuccess, setThemeSuccess] = useState("");

  const handleThemeSave = async () => {
    setThemeSubmitting(true);
    setThemeSuccess("");
    try {
      await api.patch("/api/company", { active_theme: theme.name });
      setThemeSuccess("Theme saved successfully.");
      setTimeout(() => setThemeSuccess(""), 3000);
    } catch {
      // Non-fatal — theme still applies locally
    } finally {
      setThemeSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Palette className="h-5 w-5" />
          Theme Management
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Theme selector */}
        <div>
          <Label className="mb-1.5 block">Color Theme</Label>
          <Select value={theme.name} onValueChange={setThemeName}>
            <SelectTrigger className="w-full sm:w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DEFAULT_THEMES.map((t) => (
                <SelectItem key={t.name} value={t.name}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Theme preview strip */}
        <div>
          <Label className="mb-1.5 block">Preview</Label>
          <div className="flex gap-2">
            {(() => {
              const colors = mode === "dark" ? theme.dark : theme.light;
              const swatches = [
                { label: "Primary", value: colors.primary },
                { label: "Sidebar", value: colors.sidebar },
                { label: "Active", value: colors.sidebarActive },
                { label: "Background", value: colors.background },
                { label: "Muted", value: colors.muted },
                { label: "Destructive", value: colors.destructive },
              ];
              return swatches.map((s) => (
                <div key={s.label} className="flex flex-col items-center gap-1">
                  <div
                    className="h-8 w-8 rounded-md border border-border"
                    style={{ backgroundColor: `hsl(${s.value})` }}
                  />
                  <span className="text-xs text-muted-foreground">{s.label}</span>
                </div>
              ));
            })()}
          </div>
        </div>

        {/* Dark mode toggle */}
        <div className="flex items-center justify-between">
          <div>
            <Label>Dark Mode</Label>
            <p className="text-xs text-muted-foreground">
              Toggle between light and dark appearance
            </p>
          </div>
          <Switch
            checked={mode === "dark"}
            onCheckedChange={toggleMode}
          />
        </div>

        {themeSuccess && (
          <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded p-2">
            {themeSuccess}
          </p>
        )}

        <div className="flex justify-end">
          <Button onClick={handleThemeSave} disabled={themeSubmitting} variant="outline">
            {themeSubmitting ? "Saving..." : "Save Theme"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
