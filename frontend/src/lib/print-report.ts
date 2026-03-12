/**
 * A4 report print utility.
 *
 * Generates a clean, self-contained HTML document inside a hidden iframe
 * and triggers the browser's print dialog.  This ensures all reports use
 * the same professional template regardless of the current page layout.
 */

// ── Types ──

export interface PrintReportColumn {
  key: string;
  label: string;
  align?: "left" | "right";
}

export interface PrintReportData {
  /** Report title displayed below the company header */
  reportTitle: string;
  /** Column definitions */
  columns: PrintReportColumn[];
  /** Row data — each row is a plain object keyed by column key */
  rows: Record<string, unknown>[];
  /** Formatted grand total value (already formatted as string) or null */
  grandTotal: string | null;
  /** Optional payment mode breakdown rows */
  paymentModes?: { payment_mode_name: string; amount: string }[];
  /** Metadata shown in the subtitle area */
  meta: {
    dateLabel: string;        // e.g. "From 01-Mar-2026 To 11-Mar-2026" or "Date: 11-Mar-2026"
    branchName?: string;
    routeName?: string;
    generatedBy: string;
    generatedAt: string;      // formatted date-time string
  };
}

// ── Helpers ──

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ── HTML builder ──

function buildA4Html(data: PrintReportData): string {
  const { reportTitle, columns, rows, grandTotal, paymentModes, meta } = data;

  // Subtitle parts
  const subtitleParts: string[] = [meta.dateLabel];
  if (meta.branchName) subtitleParts.push(`Branch: ${meta.branchName}`);
  if (meta.routeName) subtitleParts.push(`Route: ${meta.routeName}`);
  const subtitle = subtitleParts.join("  |  ");

  // Table header
  const thCells = columns
    .map(
      (col) =>
        `<th style="text-align:${col.align === "right" ? "right" : "left"};padding:6px 8px;">${esc(col.label)}</th>`
    )
    .join("");

  // Table body rows
  const tbodyRows = rows
    .map((row, idx) => {
      const bg = idx % 2 === 0 ? "#fff" : "#f5f5f5";
      const cells = columns
        .map((col) => {
          const val = row[col.key];
          const display = val === null || val === undefined ? "\u2014" : String(val);
          return `<td style="text-align:${col.align === "right" ? "right" : "left"};padding:5px 8px;">${esc(display)}</td>`;
        })
        .join("");
      return `<tr style="background:${bg};">${cells}</tr>`;
    })
    .join("");

  // Grand total row
  let totalRow = "";
  if (grandTotal !== null) {
    const totalCells = columns
      .map((col, idx) => {
        if (idx === 0) return `<td style="padding:6px 8px;font-weight:bold;">Grand Total</td>`;
        if (idx === columns.length - 1)
          return `<td style="text-align:right;padding:6px 8px;font-weight:bold;">${esc(grandTotal)}</td>`;
        return `<td style="padding:6px 8px;"></td>`;
      })
      .join("");
    totalRow = `<tr style="background:#e0e0e0;font-weight:bold;">${totalCells}</tr>`;
  }

  // Payment modes section
  let pmSection = "";
  if (paymentModes && paymentModes.length > 0) {
    const pmRows = paymentModes
      .map(
        (pm) =>
          `<tr><td style="padding:4px 8px;">${esc(pm.payment_mode_name)}</td><td style="text-align:right;padding:4px 8px;">${esc(pm.amount)}</td></tr>`
      )
      .join("");
    pmSection = `
      <div style="margin-top:20px;">
        <h3 style="font-size:11px;font-weight:bold;margin-bottom:6px;">Payment Mode Breakdown</h3>
        <table style="width:auto;border-collapse:collapse;border:0.5px solid #999;">
          <thead><tr style="background:#333;color:#fff;">
            <th style="text-align:left;padding:5px 8px;font-size:9px;">Payment Mode</th>
            <th style="text-align:right;padding:5px 8px;font-size:9px;">Amount</th>
          </tr></thead>
          <tbody>${pmRows}</tbody>
        </table>
      </div>`;
  }

  return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>${esc(reportTitle)}</title>
<style>
  @page { size: A4; margin: 10mm; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: "Segoe UI", Arial, Helvetica, sans-serif;
    font-size: 10px;
    color: #000;
    padding: 10mm;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .header { text-align: center; margin-bottom: 8px; }
  .header h1 { font-size: 13px; font-weight: bold; }
  .header h2 { font-size: 11px; font-weight: bold; margin-top: 4px; }
  .header .subtitle { font-size: 9px; margin-top: 4px; color: #333; }
  .header .meta { font-size: 8px; color: #666; margin-top: 4px; }
  .header hr { margin-top: 6px; border: none; border-top: 1px solid #ccc; }
  table.report { width: 100%; border-collapse: collapse; margin-top: 8px; border: 0.5px solid #999; }
  table.report th { background: #333; color: #fff; font-size: 9px; font-weight: bold; }
  table.report td { font-size: 9px; border-bottom: 0.5px solid #ddd; }
  .footer { margin-top: 10px; font-size: 8px; color: #666; text-align: right; }
  @media print {
    body { margin: 0; padding: 8mm; }
  }
</style></head><body>
<div class="header">
  <h1>SUVARNADURGA SHIPPING &amp; MARINE SERVICES PVT. LTD.</h1>
  <h2>${esc(reportTitle)}</h2>
  <div class="subtitle">${esc(subtitle)}</div>
  <div class="meta">Generated by: ${esc(meta.generatedBy)} | ${esc(meta.generatedAt)}</div>
  <hr/>
</div>
<table class="report">
  <thead><tr>${thCells}</tr></thead>
  <tbody>${tbodyRows}${totalRow}</tbody>
</table>
${pmSection}
<div class="footer">Rows: ${rows.length}</div>
</body></html>`;
}

// ── Print via hidden iframe ──

export async function printA4Report(data: PrintReportData): Promise<void> {
  const html = buildA4Html(data);

  const iframe = document.createElement("iframe");
  iframe.style.position = "fixed";
  iframe.style.left = "-9999px";
  iframe.style.top = "-9999px";
  iframe.style.width = "0";
  iframe.style.height = "0";
  iframe.style.border = "none";
  document.body.appendChild(iframe);

  const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
  if (!iframeDoc) {
    document.body.removeChild(iframe);
    throw new Error("Could not access iframe document for printing.");
  }

  iframeDoc.open();
  iframeDoc.write(html);
  iframeDoc.close();

  // Allow rendering
  await new Promise((r) => setTimeout(r, 150));

  iframe.contentWindow?.print();

  // Clean up after print dialog closes
  setTimeout(() => {
    try {
      document.body.removeChild(iframe);
    } catch {
      // iframe may already be removed
    }
  }, 5000);
}
