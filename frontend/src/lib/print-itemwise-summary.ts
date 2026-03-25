// ── Constants ──

const LINE_WIDTH = 40;
const SEPARATOR = "----------------------------------------"; // exactly 40

const COL_ITEM = 22;
const COL_RATE = 6;
const COL_QTY = 4;
const COL_NET = 8;
// COL_ITEM + COL_RATE + COL_QTY + COL_NET = 40 (fills line exactly)

// ── Types ──

export interface ItemWiseSummaryRow {
  item_name: string;
  rate: number | string;
  quantity: number | string;
  net: number | string;
}

export interface ItemWisePaymentBreakdown {
  payment_mode_name: string;
  amount: number | string;
}

export interface ItemWiseSummaryMetaData {
  companyName: string;
  branchName: string;
  dateFrom: string; // YYYY-MM-DD
  dateTo: string; // YYYY-MM-DD
  routeName?: string;
  paymentMode?: string;
  totals?: number;
  paymentBreakdown?: ItemWisePaymentBreakdown[];
}

// ── Width Safety ──

/** Hard-cap any line at LINE_WIDTH. No line may ever exceed 40 chars. */
function enforceWidth(line: string): string {
  return line.length > LINE_WIDTH ? line.slice(0, LINE_WIDTH) : line;
}

// ── Alignment Helpers ──

/** Left-align `text` in exactly `width` chars (truncates if longer). */
export function padRight(text: string, width: number): string {
  return text.substring(0, width).padEnd(width, " ");
}

/** Right-align `text` in exactly `width` chars (truncates if longer). */
export function padLeft(text: string, width: number): string {
  return text.substring(0, width).padStart(width, " ");
}

/**
 * Center `text` in exactly `width` chars.
 * Produces a string of length === width for every input.
 */
export function centerAlign(text: string, width: number = LINE_WIDTH): string {
  if (text.length >= width) return text.substring(0, width);
  const pad = width - text.length;
  const leftPad = Math.floor(pad / 2);
  return " ".repeat(leftPad) + text + " ".repeat(pad - leftPad);
}

// ── Formatting Helpers ──

function fmtNum(n: number | string): string {
  const num = typeof n === "string" ? parseFloat(n) : n;
  if (isNaN(num)) return "0.00";
  return num.toFixed(2);
}

function fmtDate(isoDate: string): string {
  const parts = isoDate.split("-");
  if (parts.length !== 3) return isoDate;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

function fmtQty(quantity: number | string): string {
  const n = typeof quantity === "string" ? parseFloat(quantity) : quantity;
  if (isNaN(n)) return "0";
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

/**
 * Normalize payment mode names to their canonical thermal-print labels.
 *   Cash / CASH   → CASH MEMO
 *   UPI / GPay    → GPAY
 *   Online        → ONLINE
 * Falls back to the raw uppercased name for any unrecognised mode.
 */
const PAYMENT_LABEL_MAP: Record<string, string> = {
  CASH: "CASH MEMO",
  "CASH MEMO": "CASH MEMO",
  UPI: "GPAY",
  GPAY: "GPAY",
  "UPI/GPAY": "GPAY",
  "UPI / GPAY": "GPAY",
  PHONEPE: "GPAY",
  PAYTM: "GPAY",
  ONLINE: "ONLINE",
};

function normalizePaymentLabel(name: string): string {
  const upper = name.trim().toUpperCase();
  if (PAYMENT_LABEL_MAP[upper]) return PAYMENT_LABEL_MAP[upper];
  if (upper.includes("CASH")) return "CASH MEMO";
  if (
    upper.includes("UPI") ||
    upper.includes("GPAY") ||
    upper.includes("PHONE") ||
    upper.includes("PAYTM")
  )
    return "GPAY";
  if (upper.includes("ONLINE")) return "ONLINE";
  return upper;
}

/**
 * Build all print lines for one item row.
 *
 * Strategy — greedy first-line fill:
 *   • Add words to firstLine as long as the result fits in COL_ITEM.
 *   • FIRST line always carries rate / qty / net columns.
 *   • Any remaining words wrap onto subsequent lines (text only, no columns).
 *   • Never cuts a word mid-way.
 */
function buildItemLines(
  name: string,
  rateStr: string,
  qtyStr: string,
  netStr: string
): string[] {
  const words = name.split(" ").filter(Boolean);
  let firstLine = "";

  for (const word of words) {
    const test = (firstLine + " " + word).trim();
    if (test.length <= COL_ITEM) {
      firstLine = test;
    } else {
      break;
    }
  }

  // Safety: always put at least the first word on line 1
  if (firstLine === "" && words.length > 0) {
    firstLine = words[0];
  }

  const lines: string[] = [];

  // FIRST line → filled item text + numeric columns
  lines.push(
    padRight(firstLine, COL_ITEM) +
      padLeft(rateStr, COL_RATE) +
      padLeft(qtyStr, COL_QTY) +
      padLeft(netStr, COL_NET)
  );

  // Overflow → word-wrapped, text only
  const remaining = name.slice(firstLine.length).trim();
  if (remaining) {
    const restWords = remaining.split(" ").filter(Boolean);
    let current = "";

    for (const word of restWords) {
      const test = (current + " " + word).trim();
      if (test.length <= COL_ITEM) {
        current = test;
      } else {
        if (current) lines.push(current);
        current = word;
      }
    }

    if (current) lines.push(current);
  }

  return lines;
}

// ── Main Formatter ──

/**
 * Returns a monospace plain-text string ready for thermal 80mm printing
 * (strict max 40 chars/line).  Render inside a <pre> tag or send to printer.
 *
 * Item-wrap rule: FIRST chunk carries rate/qty/net; overflow chunks appear
 * on subsequent lines with no numeric columns.
 */
export function formatItemWiseForPrint(
  reportData: ItemWiseSummaryRow[],
  metaData: ItemWiseSummaryMetaData
): string {
  const {
    companyName,
    branchName,
    dateFrom,
    dateTo,
    routeName,
    paymentMode,
    totals,
    paymentBreakdown,
  } = metaData;

  const push = (line: string) => raw.push(enforceWidth(line));
  const raw: string[] = [];

  // ── Header ──
  push(centerAlign(companyName.toUpperCase()));
  push(centerAlign(branchName.toUpperCase()));
  push(enforceWidth(""));
  push(centerAlign("ITEM WISE SUMMARY"));

  const dateLabel =
    dateFrom === dateTo
      ? `DATE: ${fmtDate(dateFrom)}`
      : `DATE: ${fmtDate(dateFrom)} - ${fmtDate(dateTo)}`;
  push(dateLabel);

  if (routeName) push(`ROUTE: ${routeName.toUpperCase()}`);
  if (paymentMode) push(`PAY MODE: ${paymentMode.toUpperCase()}`);

  push("");
  push(SEPARATOR);

  // ── Column Header ──
  push(
    padRight("ITEM", COL_ITEM) +
      padLeft("RATE", COL_RATE) +
      padLeft("QTY", COL_QTY) +
      padLeft("NET", COL_NET)
  );
  push(SEPARATOR);

  // ── Data Rows ──
  if (reportData.length === 0) {
    push(centerAlign("NO DATA"));
  } else {
    for (const row of reportData) {
      const itemName = String(row.item_name || "").toUpperCase();
      const rateStr = fmtNum(row.rate);
      const qtyStr = fmtQty(row.quantity);
      const netStr = fmtNum(row.net);

      const itemLines = buildItemLines(itemName, rateStr, qtyStr, netStr);
      for (const line of itemLines) {
        push(line);
      }
    }
  }

  push(SEPARATOR);

  // ── Grand Total ──
  // "TOTAL" left-anchored; amount right-anchored so combined = LINE_WIDTH exactly.
  const grandTotalStr = fmtNum(totals ?? 0);
  push(padRight("TOTAL", LINE_WIDTH - grandTotalStr.length) + grandTotalStr);

  push(SEPARATOR);

  // ── Payment Breakdown ──
  if (paymentBreakdown && paymentBreakdown.length > 0) {
    for (const pm of paymentBreakdown) {
      const label = normalizePaymentLabel(String(pm.payment_mode_name || ""));
      const amountStr = fmtNum(pm.amount);
      // Label fills left; amount right-anchored; total = LINE_WIDTH exactly.
      push(padRight(label, LINE_WIDTH - amountStr.length) + amountStr);
    }
    push(SEPARATOR);
  }

  return raw.join("\n");
}

// ── Iframe-based Thermal Printer ──

function escHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function buildPrintHtml(text: string): string {
  return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Item Wise Summary</title>
<style>
  @page { size: 80mm auto; margin: 0; }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 0;
    font-family: monospace;
    font-size: 10px;
    font-weight: 700;
    color: #000;
    -webkit-print-color-adjust: exact;
  }
  pre {
    margin: 0;
    padding: 0 2px;
    font-family: monospace;
    font-size: 10px;
    line-height: 1.2;
    width: 80mm;
    white-space: pre;
    font-weight: 700;
  }
  @media print {
    body { margin: 0; padding: 0; }
    pre  { margin: 0; padding: 0 2px; }
  }
</style></head>
<body><pre>${escHtml(text)}</pre></body></html>`;
}

export async function printItemWiseSummary(
  reportData: ItemWiseSummaryRow[],
  metaData: ItemWiseSummaryMetaData
): Promise<void> {
  const text = formatItemWiseForPrint(reportData, metaData);
  const html = buildPrintHtml(text);

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
    return;
  }

  iframeDoc.open();
  iframeDoc.write(html);
  iframeDoc.close();

  await new Promise((r) => setTimeout(r, 100));
  iframe.contentWindow?.print();

  setTimeout(() => {
    if (document.body.contains(iframe)) {
      document.body.removeChild(iframe);
    }
  }, 5000);
}
