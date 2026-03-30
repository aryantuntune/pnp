"use client";

import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { Route } from "@/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FileText, ChevronLeft, ChevronRight } from "lucide-react";

interface RateChangeLog {
  id: number;
  date: string;
  time: string;
  route_id: number;
  item_id: number;
  old_rate: number | null;
  new_rate: number | null;
  updated_by_user: string;
  updated_by_name: string | null;
  item_name: string | null;
  route_name: string | null;
  created_at: string | null;
}

function formatDate(d: string): string {
  const dt = new Date(d);
  return dt.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatTime(t: string): string {
  // Time comes as HH:MM:SS, format to 12h
  const [h, m] = t.split(":");
  const hour = parseInt(h, 10);
  const ampm = hour >= 12 ? "PM" : "AM";
  const h12 = hour % 12 || 12;
  return `${h12}:${m} ${ampm}`;
}

function formatCurrency(val: number | null): string {
  if (val === null || val === undefined) return "\u2014";
  return `\u20B9${val.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatRouteLabel(r: Route): string {
  return r.branch_one_name && r.branch_two_name
    ? `${r.branch_one_name} - ${r.branch_two_name}`
    : `Route ${r.id}`;
}

function getToday(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function getDateDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function RateChangeLogsPage() {
  const [logs, setLogs] = useState<RateChangeLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [totalCount, setTotalCount] = useState(0);

  // Filters — default: last 30 days
  const [dateFrom, setDateFrom] = useState(() => getDateDaysAgo(30));
  const [dateTo, setDateTo] = useState(getToday);
  const [routeId, setRouteId] = useState("");
  const [itemId, setItemId] = useState("");

  // Pagination
  const [page, setPage] = useState(0);
  const limit = 50;

  // Dropdown data
  const [routes, setRoutes] = useState<Route[]>([]);
  const [items, setItems] = useState<{ id: number; name: string }[]>([]);

  // Fetch dropdown data
  const fetchDropdowns = useCallback(async () => {
    try {
      const [routeResp, itemResp] = await Promise.all([
        api.get<Route[]>("/api/routes?limit=200&status=active"),
        api.get<{ id: number; name: string }[]>("/api/items?limit=200&status=active"),
      ]);
      setRoutes(routeResp.data);
      setItems(itemResp.data);
    } catch {
      // non-critical
    }
  }, []);

  useEffect(() => {
    fetchDropdowns();
  }, [fetchDropdowns]);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params: Record<string, string | number> = {
        skip: page * limit,
        limit,
      };
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (routeId) params.route_id = routeId;
      if (itemId) params.item_id = itemId;

      const [logsResp, countResp] = await Promise.all([
        api.get<RateChangeLog[]>("/api/rate-change-logs", { params }),
        api.get<number>("/api/rate-change-logs/count", {
          params: {
            ...(dateFrom ? { date_from: dateFrom } : {}),
            ...(dateTo ? { date_to: dateTo } : {}),
            ...(routeId ? { route_id: routeId } : {}),
            ...(itemId ? { item_id: itemId } : {}),
          },
        }),
      ]);
      setLogs(logsResp.data);
      setTotalCount(countResp.data);
    } catch {
      setError("Failed to load rate change logs.");
      setLogs([]);
      setTotalCount(0);
    } finally {
      setLoading(false);
    }
  }, [page, dateFrom, dateTo, routeId, itemId]);

  // Fetch on filter/page change
  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const totalPages = Math.ceil(totalCount / limit);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Rate Change Logs</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Read-only audit trail of all item rate modifications
        </p>
      </div>

      {/* Filter Panel */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Label className="mb-1.5 block">From</Label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setPage(0);
                }}
                className="w-full sm:w-[160px]"
              />
            </div>
            <div>
              <Label className="mb-1.5 block">To</Label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  setPage(0);
                }}
                className="w-full sm:w-[160px]"
              />
            </div>

            <div>
              <Label className="mb-1.5 block">Route</Label>
              <Select
                value={routeId || "all"}
                onValueChange={(v) => {
                  setRouteId(v === "all" ? "" : v);
                  setPage(0);
                }}
              >
                <SelectTrigger className="w-full sm:w-[220px]">
                  <SelectValue placeholder="All Routes" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Routes</SelectItem>
                  {routes.map((r) => (
                    <SelectItem key={r.id} value={String(r.id)}>
                      {formatRouteLabel(r)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="mb-1.5 block">Item</Label>
              <Select
                value={itemId || "all"}
                onValueChange={(v) => {
                  setItemId(v === "all" ? "" : v);
                  setPage(0);
                }}
              >
                <SelectTrigger className="w-full sm:w-[180px]">
                  <SelectValue placeholder="All Items" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Items</SelectItem>
                  {items.map((item) => (
                    <SelectItem key={item.id} value={String(item.id)}>
                      {item.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive text-sm">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <Table className="min-w-[800px]">
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className="font-semibold">Date</TableHead>
                <TableHead className="font-semibold">Time</TableHead>
                <TableHead className="font-semibold">Route</TableHead>
                <TableHead className="font-semibold">Item</TableHead>
                <TableHead className="font-semibold text-right">Old Rate</TableHead>
                <TableHead className="font-semibold text-right">New Rate</TableHead>
                <TableHead className="font-semibold">Updated By</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={`skeleton-${i}`}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-[70%] inline-block" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center">
                    <div className="flex flex-col items-center gap-2 text-muted-foreground">
                      <FileText className="h-10 w-10" />
                      <p>No rate change logs found for the selected filters.</p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((log) => (
                  <TableRow key={log.id} className="hover:bg-muted/30">
                    <TableCell>{formatDate(log.date)}</TableCell>
                    <TableCell>{formatTime(log.time)}</TableCell>
                    <TableCell>{log.route_name || `Route ${log.route_id}`}</TableCell>
                    <TableCell>{log.item_name || `Item ${log.item_id}`}</TableCell>
                    <TableCell className="text-right">{formatCurrency(log.old_rate)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(log.new_rate)}</TableCell>
                    <TableCell>{log.updated_by_name || log.updated_by_user}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Pagination */}
      {totalCount > 0 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Showing {page * limit + 1}\u2013{Math.min((page + 1) * limit, totalCount)} of{" "}
            {totalCount} {totalCount === 1 ? "log" : "logs"}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={page + 1 >= totalPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
