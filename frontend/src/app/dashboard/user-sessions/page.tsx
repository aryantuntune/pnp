"use client";

import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import DataTable, { Column } from "@/components/dashboard/DataTable";
import type {
  ActiveSession,
  SessionHistory,
  SessionUser,
} from "@/types/user-session";

/* ───── helpers ───── */

function formatDuration(
  startIso: string | null,
  endIso?: string | null
): string {
  if (!startIso) return "\u2014";
  const start = new Date(startIso).getTime();
  const end = endIso ? new Date(endIso).getTime() : Date.now();
  const diffMs = end - start;
  if (diffMs < 0) return "\u2014";
  const mins = Math.floor(diffMs / 60_000);
  const hrs = Math.floor(mins / 60);
  const remainMins = mins % 60;
  if (hrs > 0) return `${hrs}h ${remainMins}m`;
  return `${remainMins}m`;
}

function formatTime(iso: string | null): string {
  if (!iso) return "\u2014";
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

function roleBadge(role: string) {
  const colors: Record<
    string,
    "default" | "secondary" | "outline" | "destructive"
  > = {
    SUPER_ADMIN: "destructive",
    ADMIN: "default",
    MANAGER: "secondary",
    BILLING_OPERATOR: "outline",
    TICKET_CHECKER: "outline",
  };
  return (
    <Badge variant={colors[role] || "secondary"}>
      {role.replace(/_/g, " ")}
    </Badge>
  );
}

function endReasonBadge(reason: string | null) {
  if (!reason)
    return (
      <Badge variant="default" className="bg-green-600">
        Active
      </Badge>
    );
  const map: Record<
    string,
    { variant: "default" | "secondary" | "destructive"; label: string }
  > = {
    logout: { variant: "default", label: "Logout" },
    timeout: { variant: "secondary", label: "Timeout" },
    login_elsewhere: { variant: "destructive", label: "Kicked" },
  };
  const info = map[reason] || {
    variant: "secondary" as const,
    label: reason,
  };
  return <Badge variant={info.variant}>{info.label}</Badge>;
}

/* ───── page ───── */

export default function UserSessionsPage() {
  const [tab, setTab] = useState<"live" | "history">("live");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">User Sessions</h1>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-2 border-b pb-0">
        <button
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
            tab === "live"
              ? "bg-white border border-b-white -mb-px text-blue-700"
              : "text-gray-500 hover:text-gray-700"
          }`}
          onClick={() => setTab("live")}
        >
          Live Sessions
        </button>
        <button
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
            tab === "history"
              ? "bg-white border border-b-white -mb-px text-blue-700"
              : "text-gray-500 hover:text-gray-700"
          }`}
          onClick={() => setTab("history")}
        >
          Session History
        </button>
      </div>

      {tab === "live" ? <LiveSessions /> : <HistoryTab />}
    </div>
  );
}

/* ───── Live Sessions Tab ───── */

function LiveSessions() {
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.get<ActiveSession[]>(
        "/api/user-sessions/active"
      );
      setSessions(resp.data);
      setError("");
    } catch {
      setError("Failed to load active sessions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const columns: Column<ActiveSession>[] = [
    {
      key: "full_name",
      label: "User",
      render: (s) => (
        <div>
          <span className="font-medium">{s.full_name}</span>
          <span className="text-xs text-gray-400 ml-2">@{s.username}</span>
        </div>
      ),
    },
    {
      key: "role",
      label: "Role",
      render: (s) => roleBadge(s.role),
    },
    {
      key: "ip_address",
      label: "IP / City",
      render: (s) => (
        <div className="text-sm">
          <div>{s.ip_address || "\u2014"}</div>
          {s.city && <div className="text-xs text-gray-400">{s.city}</div>}
        </div>
      ),
    },
    {
      key: "started_at",
      label: "Login Time",
      render: (s) => (
        <span className="text-sm">{formatTime(s.started_at)}</span>
      ),
    },
    {
      key: "last_heartbeat" as keyof ActiveSession,
      label: "Duration",
      render: (s) => (
        <span className="text-sm font-mono">
          {formatDuration(s.started_at)}
        </span>
      ),
    },
    {
      key: "ticket_count",
      label: "Tickets",
      render: (s) =>
        s.ticket_count !== null && s.ticket_count !== undefined ? (
          <span className="font-medium">{s.ticket_count}</span>
        ) : (
          <span className="text-gray-300">\u2014</span>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {sessions.length} active session
          {sessions.length !== 1 ? "s" : ""}
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchSessions}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>
      {error && <p className="text-red-500 text-sm">{error}</p>}
      <DataTable
        columns={columns}
        data={sessions}
        totalCount={sessions.length}
        page={1}
        pageSize={sessions.length || 10}
        sortBy=""
        sortOrder="asc"
        onPageChange={() => {}}
        onPageSizeChange={() => {}}
        onSort={() => {}}
        loading={loading}
        emptyMessage="No active sessions."
      />
    </div>
  );
}

/* ───── History Tab ───── */

function HistoryTab() {
  const [sessions, setSessions] = useState<SessionHistory[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [users, setUsers] = useState<SessionUser[]>([]);

  // Load user list for filter dropdown
  useEffect(() => {
    api
      .get<SessionUser[]>("/api/user-sessions/users")
      .then((r) => setUsers(r.data))
      .catch(() => {});
  }, []);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * pageSize),
        limit: String(pageSize),
      });
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      if (userFilter) params.set("user_id", userFilter);

      const countParams = new URLSearchParams();
      if (dateFrom) countParams.set("date_from", dateFrom);
      if (dateTo) countParams.set("date_to", dateTo);
      if (userFilter) countParams.set("user_id", userFilter);

      const [dataResp, countResp] = await Promise.all([
        api.get<SessionHistory[]>(
          `/api/user-sessions/history?${params}`
        ),
        api.get<number>(
          `/api/user-sessions/history/count?${countParams}`
        ),
      ]);
      setSessions(dataResp.data);
      setTotalCount(countResp.data as unknown as number);
      setError("");
    } catch {
      setError("Failed to load session history.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, dateFrom, dateTo, userFilter]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const columns: Column<SessionHistory>[] = [
    {
      key: "full_name",
      label: "User",
      render: (s) => (
        <div>
          <span className="font-medium">{s.full_name}</span>
          <span className="text-xs text-gray-400 ml-2">@{s.username}</span>
        </div>
      ),
    },
    {
      key: "role",
      label: "Role",
      render: (s) => roleBadge(s.role),
    },
    {
      key: "started_at",
      label: "Login",
      render: (s) => (
        <span className="text-sm">{formatTime(s.started_at)}</span>
      ),
    },
    {
      key: "ended_at",
      label: "Logout",
      render: (s) => (
        <span className="text-sm">{formatTime(s.ended_at)}</span>
      ),
    },
    {
      key: "last_heartbeat" as keyof SessionHistory,
      label: "Duration",
      render: (s) => (
        <span className="text-sm font-mono">
          {formatDuration(s.started_at, s.ended_at)}
        </span>
      ),
    },
    {
      key: "end_reason",
      label: "End Reason",
      render: (s) => endReasonBadge(s.end_reason),
    },
    {
      key: "ip_address",
      label: "IP / City",
      render: (s) => (
        <div className="text-sm">
          <div>{s.ip_address || "\u2014"}</div>
          {s.city && <div className="text-xs text-gray-400">{s.city}</div>}
        </div>
      ),
    },
    {
      key: "ticket_count",
      label: "Tickets",
      render: (s) =>
        s.ticket_count !== null && s.ticket_count !== undefined ? (
          <span className="font-medium">{s.ticket_count}</span>
        ) : (
          <span className="text-gray-300">\u2014</span>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">From</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPage(1);
            }}
            className="border rounded-md px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPage(1);
            }}
            className="border rounded-md px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">User</label>
          <select
            value={userFilter}
            onChange={(e) => {
              setUserFilter(e.target.value);
              setPage(1);
            }}
            className="border rounded-md px-3 py-1.5 text-sm min-w-[180px]"
          >
            <option value="">All Users</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name} ({u.role.replace(/_/g, " ")})
              </option>
            ))}
          </select>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setDateFrom("");
            setDateTo("");
            setUserFilter("");
            setPage(1);
          }}
        >
          Clear Filters
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchHistory}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      <DataTable
        columns={columns}
        data={sessions}
        totalCount={totalCount}
        page={page}
        pageSize={pageSize}
        sortBy=""
        sortOrder="asc"
        onPageChange={setPage}
        onPageSizeChange={(size: number) => {
          setPageSize(size);
          setPage(1);
        }}
        onSort={() => {}}
        loading={loading}
        emptyMessage="No session history found."
      />
    </div>
  );
}
