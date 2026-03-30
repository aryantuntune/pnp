/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * QZ Tray service — direct printing without the browser print dialog.
 * QZ Tray must be installed and running on the POS machine (https://qz.io).
 * In QZ Tray settings, "Allow Unsigned" must be enabled.
 */

const PRINTER_KEY = "ssmspl_qz_printer";

export function getStoredPrinterName(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(PRINTER_KEY) || "";
}

export function setStoredPrinterName(name: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(PRINTER_KEY, name);
}

// Lazily load qz-tray (must be client-side only — it uses WebSocket / window)
let qzCache: any = null;
async function getQz(): Promise<any> {
  if (qzCache) return qzCache;
  const mod = await import("qz-tray");
  qzCache = (mod as any).default ?? mod;
  return qzCache;
}

// Configure unsigned mode — QZ Tray must have "Allow Unsigned" checked in its
// settings (right-click tray icon → Site Manager → uncheck "Block Unsigned")
function applyUnsignedSecurity(qz: any) {
  qz.security.setCertificatePromise((_resolve: any, _reject: any) => {
    _resolve("");
  });
  qz.security.setSignaturePromise((_toSign: any, _resolve: any, _reject: any) => {
    _resolve("");
  });
}

export function qzIsConnected(): boolean {
  try {
    if (!qzCache) return false;
    return qzCache.websocket.isActive();
  } catch {
    return false;
  }
}

/**
 * Connect to QZ Tray. Returns true if connected, false if QZ Tray is not
 * running or not installed.
 */
export async function qzConnect(): Promise<boolean> {
  try {
    const qz = await getQz();
    if (qz.websocket.isActive()) return true;
    applyUnsignedSecurity(qz);
    await Promise.race([
      qz.websocket.connect({ retries: 1, delay: 0.5 }),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error("QZ Tray connection timeout")), 5000)
      ),
    ]);
    return qz.websocket.isActive();
  } catch {
    return false;
  }
}

export async function qzDisconnect(): Promise<void> {
  try {
    const qz = await getQz();
    if (qz.websocket.isActive()) await qz.websocket.disconnect();
  } catch {
    // ignore
  }
}

/**
 * List all printers visible to QZ Tray. Connects if not already connected.
 */
export async function qzListPrinters(): Promise<string[]> {
  const qz = await getQz();
  if (!qz.websocket.isActive()) {
    const ok = await qzConnect();
    if (!ok) return [];
  }
  try {
    const result = await qz.printers.find("");
    if (!result) return [];
    return Array.isArray(result) ? result : [result];
  } catch {
    return [];
  }
}

/**
 * Print a full HTML document directly to the named printer via QZ Tray.
 * @param printerName  Exact printer name as returned by qzListPrinters()
 * @param html         Full HTML document string (<!DOCTYPE html>…</html>)
 * @param widthMm      Paper width in mm (58 or 80)
 */
export async function qzPrint(
  printerName: string,
  html: string,
  widthMm: number,
): Promise<void> {
  const qz = await getQz();
  if (!qz.websocket.isActive()) {
    applyUnsignedSecurity(qz);
    await qz.websocket.connect({ retries: 1, delay: 0.5 });
  }

  const config = qz.configs.create(printerName, {
    colorType: "blackWhite",
    size: { width: widthMm, height: null }, // null = auto-height
    units: "mm",
    margins: 0,
    scaleContent: false,
  });

  await qz.print(config, [
    {
      type: "pixel",
      format: "html",
      flavor: "plain",
      data: html,
    },
  ]);
}
