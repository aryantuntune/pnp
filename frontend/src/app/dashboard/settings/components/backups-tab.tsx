"use client";

import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { BackupFile, BackupStatus, BackupNotificationRecipient } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  HardDrive,
  Clock,
  CalendarClock,
  Timer,
  Download,
  Mail,
  Plus,
  Trash2,
  Power,
  RefreshCw,
  CheckCircle,
  CloudOff,
  Loader2,
} from "lucide-react";

function formatDate(iso: string | null): string {
  if (!iso) return "\u2014";
  try {
    return new Date(iso).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

export default function BackupsTab() {
  // ── Status state ──
  const [status, setStatus] = useState<BackupStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState("");

  // ── Trigger state ──
  const [triggering, setTriggering] = useState(false);
  const [triggerMessage, setTriggerMessage] = useState("");
  const [triggerError, setTriggerError] = useState("");

  // ── History state ──
  const [history, setHistory] = useState<BackupFile[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");

  // ── Notification recipients state ──
  const [recipients, setRecipients] = useState<BackupNotificationRecipient[]>([]);
  const [recipientsLoading, setRecipientsLoading] = useState(true);
  const [recipientsError, setRecipientsError] = useState("");
  const [recipientsSuccess, setRecipientsSuccess] = useState("");
  const [addEmail, setAddEmail] = useState("");
  const [addLabel, setAddLabel] = useState("");
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  // ── Download state ──
  const [downloadingFile, setDownloadingFile] = useState<string | null>(null);

  // ── Fetch helpers ──

  const fetchStatus = useCallback(async () => {
    try {
      const { data } = await api.get<BackupStatus>("/api/settings/backup/status");
      setStatus(data);
      setStatusError("");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to load backup status.";
      setStatusError(msg);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const { data } = await api.get<BackupFile[]>("/api/settings/backup/history");
      setHistory(data);
      setHistoryError("");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to load backup history.";
      setHistoryError(msg);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const fetchRecipients = useCallback(async () => {
    try {
      const { data } = await api.get<BackupNotificationRecipient[]>(
        "/api/settings/backup/recipients"
      );
      setRecipients(data);
      setRecipientsError("");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to load notification recipients.";
      setRecipientsError(msg);
    } finally {
      setRecipientsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchHistory();
    fetchRecipients();
  }, [fetchStatus, fetchHistory, fetchRecipients]);

  // ── Trigger backup ──

  const handleTriggerBackup = async () => {
    setTriggering(true);
    setTriggerMessage("");
    setTriggerError("");

    // Capture current backup time so we know when a new one completes
    const prevBackupTime = status?.last_backup_time ?? null;

    try {
      const { data } = await api.post<{ message: string; status: string }>(
        "/api/settings/backup/trigger"
      );
      setTriggerMessage(data.message || "Backup triggered. Waiting for completion...");

      // Poll every 3 seconds until status changes or 90 seconds timeout
      let elapsed = 0;
      const POLL_INTERVAL = 3000;
      const POLL_TIMEOUT = 90000;

      const pollTimer = setInterval(async () => {
        elapsed += POLL_INTERVAL;
        try {
          const { data: newStatus } = await api.get<BackupStatus>(
            "/api/settings/backup/status"
          );
          const done =
            newStatus.last_backup_time !== prevBackupTime && !newStatus.backup_in_progress;

          if (done || elapsed >= POLL_TIMEOUT) {
            clearInterval(pollTimer);
            setStatus(newStatus);
            fetchHistory();
            setTriggering(false);

            if (done) {
              const ok = newStatus.last_backup_status === "success";
              setTriggerMessage(
                ok
                  ? `Backup completed successfully (${newStatus.last_backup_size ?? ""})`
                  : "Backup finished with errors. Check status above."
              );
            } else {
              setTriggerMessage(
                "Backup is taking longer than expected. Check status manually."
              );
            }
            setTimeout(() => setTriggerMessage(""), 8000);
          }
        } catch {
          // Polling failure — just wait for next tick
        }
      }, POLL_INTERVAL);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to trigger backup.";
      setTriggerError(msg);
      setTimeout(() => setTriggerError(""), 5000);
      setTriggering(false);
    }
  };

  // ── Download file ──

  const handleDownload = async (filename: string) => {
    setDownloadingFile(filename);
    try {
      const res = await api.get(`/api/settings/backup/download/${filename}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to download file.";
      setHistoryError(msg);
      setTimeout(() => setHistoryError(""), 5000);
    } finally {
      setDownloadingFile(null);
    }
  };

  // ── Recipient handlers ──

  const handleAddRecipient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addEmail.trim()) return;

    setAddSubmitting(true);
    setRecipientsError("");
    setRecipientsSuccess("");
    try {
      await api.post("/api/settings/backup/recipients", {
        email: addEmail.trim(),
        label: addLabel.trim() || undefined,
      });
      setAddEmail("");
      setAddLabel("");
      await fetchRecipients();
      setRecipientsSuccess("Recipient added successfully.");
      setTimeout(() => setRecipientsSuccess(""), 3000);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      let msg: string;
      if (typeof detail === "string") {
        msg = detail;
      } else if (Array.isArray(detail)) {
        msg = detail.map((e: { msg?: string }) => e.msg || "Validation error").join("; ");
      } else {
        msg = "Failed to add recipient.";
      }
      setRecipientsError(msg);
    } finally {
      setAddSubmitting(false);
    }
  };

  const handleToggleRecipient = async (id: number) => {
    setTogglingId(id);
    setRecipientsError("");
    setRecipientsSuccess("");
    try {
      const { data: updated } = await api.patch<BackupNotificationRecipient>(
        `/api/settings/backup/recipients/${id}`
      );
      setRecipients((prev) => prev.map((r) => (r.id === id ? updated : r)));
      setRecipientsSuccess(
        `Recipient ${updated.is_active ? "activated" : "deactivated"} successfully.`
      );
      setTimeout(() => setRecipientsSuccess(""), 3000);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to update recipient.";
      setRecipientsError(msg);
    } finally {
      setTogglingId(null);
    }
  };

  const handleDeleteRecipient = async (id: number) => {
    setDeletingId(id);
    setRecipientsError("");
    setRecipientsSuccess("");
    try {
      await api.delete(`/api/settings/backup/recipients/${id}`);
      setRecipients((prev) => prev.filter((r) => r.id !== id));
      setConfirmDeleteId(null);
      setRecipientsSuccess("Recipient removed successfully.");
      setTimeout(() => setRecipientsSuccess(""), 3000);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to delete recipient.";
      setRecipientsError(msg);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* ── Status cards ── */}
      {statusLoading ? (
        <div className="flex items-center justify-center py-8 text-muted-foreground">
          Loading backup status...
        </div>
      ) : statusError ? (
        <p className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded p-3">
          {statusError}
        </p>
      ) : status ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Last Backup */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <div className="rounded-md bg-accent p-2">
                  <Clock className="h-5 w-5 text-accent-foreground" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-muted-foreground">Last Backup</p>
                  <p className="text-sm font-medium truncate mt-0.5">
                    {formatDate(status.last_backup_time)}
                  </p>
                  {status.last_backup_size && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {status.last_backup_size}
                    </p>
                  )}
                  {status.last_backup_status && (
                    <Badge
                      variant={status.last_backup_status === "success" ? "default" : "secondary"}
                      className="mt-1"
                    >
                      {status.last_backup_status}
                    </Badge>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Schedule */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <div className="rounded-md bg-accent p-2">
                  <CalendarClock className="h-5 w-5 text-accent-foreground" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-muted-foreground">Schedule</p>
                  <p className="text-sm font-medium mt-0.5">
                    {status.schedule || "\u2014"}
                  </p>
                  {status.last_sync_status && (
                    <p className="text-xs text-muted-foreground mt-1">
                      GDrive sync: {status.last_sync_status}
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Retention */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <div className="rounded-md bg-accent p-2">
                  <Timer className="h-5 w-5 text-accent-foreground" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-muted-foreground">Retention</p>
                  <p className="text-sm font-medium mt-0.5">
                    Local: {status.local_retention_days} days
                  </p>
                  <p className="text-sm font-medium">
                    GDrive: {status.gdrive_retention_days} days
                  </p>
                  {status.gdrive_backup_count != null && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {status.gdrive_backup_count} file{status.gdrive_backup_count !== 1 ? "s" : ""} on GDrive
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* ── Manual backup trigger ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <HardDrive className="h-5 w-5" />
            Manual Backup
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Trigger a database backup immediately. The backup will be created and optionally synced to Google Drive.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button onClick={handleTriggerBackup} disabled={triggering}>
            {triggering ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Backup in progress...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Trigger Backup Now
              </>
            )}
          </Button>

          {triggerMessage && (
            <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded p-2">
              {triggerMessage}
            </p>
          )}

          {triggerError && (
            <p className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded p-2">
              {triggerError}
            </p>
          )}
        </CardContent>
      </Card>

      {/* ── Notification recipients ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Mail className="h-5 w-5" />
            Backup Notification Recipients
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Manage who receives email notifications when backups complete or fail
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Add recipient form */}
          <form onSubmit={handleAddRecipient} className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[200px]">
              <Label className="mb-1.5 block">Email *</Label>
              <Input
                type="email"
                required
                placeholder="e.g. admin@ssmspl.com"
                value={addEmail}
                onChange={(e) => setAddEmail(e.target.value)}
              />
            </div>
            <div className="min-w-[140px]">
              <Label className="mb-1.5 block">Label</Label>
              <Input
                placeholder="e.g. DBA"
                value={addLabel}
                onChange={(e) => setAddLabel(e.target.value)}
                maxLength={100}
              />
            </div>
            <Button type="submit" disabled={addSubmitting}>
              <Plus className="h-4 w-4 mr-2" />
              {addSubmitting ? "Adding..." : "Add"}
            </Button>
          </form>

          {recipientsError && (
            <p className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded p-2">
              {recipientsError}
            </p>
          )}

          {recipientsSuccess && (
            <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded p-2">
              {recipientsSuccess}
            </p>
          )}

          {recipientsLoading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              Loading recipients...
            </div>
          ) : recipients.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              No recipients configured. Add an email address above.
            </div>
          ) : (
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Label</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recipients.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-medium">{r.email}</TableCell>
                      <TableCell>{r.label || "\u2014"}</TableCell>
                      <TableCell>
                        <Badge variant={r.is_active ? "default" : "secondary"}>
                          {r.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={togglingId === r.id}
                            onClick={() => handleToggleRecipient(r.id)}
                            title={r.is_active ? "Deactivate" : "Activate"}
                          >
                            <Power className="h-4 w-4 mr-1" />
                            {togglingId === r.id
                              ? "..."
                              : r.is_active
                                ? "Deactivate"
                                : "Activate"}
                          </Button>
                          {confirmDeleteId === r.id ? (
                            <div className="flex items-center gap-1">
                              <Button
                                variant="destructive"
                                size="sm"
                                disabled={deletingId === r.id}
                                onClick={() => handleDeleteRecipient(r.id)}
                              >
                                {deletingId === r.id ? "..." : "Confirm"}
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setConfirmDeleteId(null)}
                              >
                                Cancel
                              </Button>
                            </div>
                          ) : (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setConfirmDeleteId(r.id)}
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4 mr-1" />
                              Delete
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Recent backups table ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <HardDrive className="h-5 w-5" />
            Recent Backups
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            View and download recent database backup files
          </p>
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              Loading backup history...
            </div>
          ) : historyError ? (
            <p className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded p-2">
              {historyError}
            </p>
          ) : history.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              No backup files found.
            </div>
          ) : (
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Filename</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>GDrive</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.map((file) => (
                    <TableRow key={file.filename}>
                      <TableCell className="font-medium font-mono text-xs">
                        {file.filename}
                      </TableCell>
                      <TableCell className="text-sm">{file.size_human}</TableCell>
                      <TableCell className="text-sm">
                        {formatDate(file.created_at)}
                      </TableCell>
                      <TableCell>
                        {file.gdrive_synced === true ? (
                          <span className="flex items-center gap-1 text-sm text-green-700">
                            <CheckCircle className="h-4 w-4" />
                            Synced
                          </span>
                        ) : file.gdrive_synced === false ? (
                          <span className="flex items-center gap-1 text-sm text-yellow-600">
                            <Clock className="h-4 w-4" />
                            Pending
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-sm text-muted-foreground">
                            <CloudOff className="h-4 w-4" />
                            N/A
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={downloadingFile === file.filename}
                          onClick={() => handleDownload(file.filename)}
                        >
                          {downloadingFile === file.filename ? (
                            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                          ) : (
                            <Download className="h-4 w-4 mr-1" />
                          )}
                          {downloadingFile === file.filename ? "Downloading..." : "Download"}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
