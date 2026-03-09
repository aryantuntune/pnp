import { PaperWidth } from "@/lib/print-receipt";

// ── Types ──

export interface BranchSummaryPrintData {
  branchName: string;
  dateFrom: string; // YYYY-MM-DD
  dateTo: string; // YYYY-MM-DD
  items: { item_name: string; rate: number; quantity: number; net: number }[];
  grandTotal: number;
  paymentModes: { payment_mode_name: string; amount: number }[];
  paperWidth: PaperWidth;
}

// ── Helpers ──

function escHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function fmtNum(n: number): string {
  return n.toFixed(2);
}

function formatDDMMYYYY(isoDate: string): string {
  const [y, m, d] = isoDate.split("-");
  return `${d}/${m}/${y}`;
}

// ── HTML builder ──

function buildBranchSummaryHtml(data: BranchSummaryPrintData): string {
  const { branchName, dateFrom, dateTo, items, grandTotal, paymentModes, paperWidth } = data;

  const widthMm = paperWidth === "58mm" ? 58 : 80;
  const fontSize = paperWidth === "58mm" ? "11px" : "12px";

  const dateLabel =
    dateFrom === dateTo
      ? `Item wise summary list For Date : ${formatDDMMYYYY(dateFrom)}`
      : `Item wise summary list From : ${formatDDMMYYYY(dateFrom)} To : ${formatDDMMYYYY(dateTo)}`;

  const itemRows = items
    .map(
      (item) =>
        `<tr>` +
        `<td class="item-name">${escHtml(item.item_name)}</td>` +
        `<td class="r">${fmtNum(item.rate)}</td>` +
        `<td class="r">${item.quantity.toFixed(1)}</td>` +
        `<td class="r">${fmtNum(item.net)}</td>` +
        `</tr>`
    )
    .join("");

  const paymentRows = paymentModes
    .map(
      (pm) =>
        `<tr>` +
        `<td colspan="3" class="r pm-label">${escHtml(pm.payment_mode_name)}</td>` +
        `<td class="r">${fmtNum(pm.amount)}</td>` +
        `</tr>`
    )
    .join("");

  return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Branch Item Summary</title>
<style>
  @page { size: ${widthMm}mm auto; margin: 0; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: "Courier New", Courier, monospace;
    font-size: ${fontSize};
    font-weight: 700;
    width: ${widthMm}mm;
    padding: 2mm 2mm;
    line-height: 1.3;
    color: #000;
    -webkit-print-color-adjust: exact;
  }
  .center { text-align: center; }
  .bold { font-weight: 900; }
  .dash { border-top: 2px dashed #000; margin: 3px 0; }
  .r { text-align: right; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 1px 2px; vertical-align: top; }
  td.r { text-align: right; white-space: nowrap; }
  td.item-name { word-break: break-word; }
  td.pm-label { padding-right: 6px; }
  col.name { width: auto; }
  col.num { width: ${paperWidth === "58mm" ? "40px" : "48px"}; }
  @media print {
    body { margin: 0; padding: 2mm 2mm; transform: scale(0.92); transform-origin: top center; }
  }
</style></head><body>
<div class="center bold">SUVARNADURGA SHIPPING &amp;</div>
<div class="center bold">MARINE SERVICES PVT.LTD</div>
<br/>
<div class="center bold">${escHtml(branchName.toUpperCase())}</div>
<br/>
<div class="center">${escHtml(dateLabel)}</div>
<div class="dash"></div>
<table>
<colgroup><col class="name"/><col class="num"/><col class="num"/><col class="num"/></colgroup>
<tr class="bold"><td>Item</td><td class="r">Rate</td><td class="r">Qty</td><td class="r">Net</td></tr>
<tr><td colspan="4"><div class="dash"></div></td></tr>
${itemRows}
</table>
<div class="dash"></div>
<table>
<colgroup><col class="name"/><col class="num"/><col class="num"/><col class="num"/></colgroup>
<tr class="bold"><td colspan="3" class="r"></td><td class="r">${fmtNum(grandTotal)}</td></tr>
${paymentRows.length > 0 ? `<tr><td colspan="4">&nbsp;</td></tr>${paymentRows}` : ""}
</table>
</body></html>`;
}

// ── Print via hidden iframe ──

export async function printBranchItemSummary(data: BranchSummaryPrintData): Promise<void> {
  const html = buildBranchSummaryHtml(data);

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

  // Small delay for rendering
  await new Promise((r) => setTimeout(r, 100));

  iframe.contentWindow?.print();

  // Clean up after a delay to allow print dialog
  setTimeout(() => {
    document.body.removeChild(iframe);
  }, 5000);
}
