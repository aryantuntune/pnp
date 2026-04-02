"use client";

import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { DailyReportRecipient } from "@/types";
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
import { Mail, Plus, Trash2, Power } from "lucide-react";

export default function NotificationsTab() {
  const [recipients, setRecipients] = useState<DailyReportRecipient[]>([]);
  const [recipientsLoading, setRecipientsLoading] = useState(true);
  const [recipientsError, setRecipientsError] = useState("");
  const [recipientsSuccess, setRecipientsSuccess] = useState("");
  const [addEmail, setAddEmail] = useState("");
  const [addLabel, setAddLabel] = useState("");
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const fetchRecipients = useCallback(async () => {
    try {
      const { data } = await api.get<DailyReportRecipient[]>(
        "/api/settings/daily-report-recipients"
      );
      setRecipients(data);
      setRecipientsError("");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to load recipients.";
      setRecipientsError(msg);
    } finally {
      setRecipientsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRecipients();
  }, [fetchRecipients]);

  const handleAddRecipient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addEmail.trim()) return;

    setAddSubmitting(true);
    setRecipientsError("");
    setRecipientsSuccess("");
    try {
      await api.post("/api/settings/daily-report-recipients", {
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
      const { data: updated } = await api.patch<DailyReportRecipient>(
        `/api/settings/daily-report-recipients/${id}`
      );
      setRecipients((prev) =>
        prev.map((r) => (r.id === id ? updated : r))
      );
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
      await api.delete(`/api/settings/daily-report-recipients/${id}`);
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
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Mail className="h-5 w-5" />
          Daily Report Recipients
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Manage who receives the daily summary email at 11:59 PM
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
              placeholder="e.g. CEO"
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

        {/* Recipients table */}
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
  );
}
