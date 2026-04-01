/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * QZ Tray service — direct printing without the browser print dialog.
 * QZ Tray must be installed and running on the POS machine (https://qz.io).
 * Uses QZ Tray's demo certificate for silent trusted printing (no popup).
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

// ── SSMSPL signing certificate ──
// Self-signed cert generated for SSMSPL POS printing.
// The corresponding ssmspl-qz.crt must be imported into QZ Tray Site Manager (one time per machine).
const DEMO_CERT = `-----BEGIN CERTIFICATE-----
MIIDczCCAlugAwIBAgIUE75Z8l7av7Cbn4cJNRew+55+3NowDQYJKoZIhvcNAQEL
BQAwSTELMAkGA1UEBhMCSU4xFDASBgNVBAgMC01haGFyYXNodHJhMQ8wDQYDVQQK
DAZTU01TUEwxEzARBgNVBAMMClNTTVNQTCBQT1MwHhcNMjYwMzMxMjAwODU4WhcN
MzYwMzI4MjAwODU4WjBJMQswCQYDVQQGEwJJTjEUMBIGA1UECAwLTWFoYXJhc2h0
cmExDzANBgNVBAoMBlNTTVNQTDETMBEGA1UEAwwKU1NNU1BMIFBPUzCCASIwDQYJ
KoZIhvcNAQEBBQADggEPADCCAQoCggEBAN0DjPw375xr1ekRgc+SFzpJ85rz6phg
wzEenwvbYHX0A57lY7JrjvQ+T91dVRh3iLrNkT5h/zvBlWNw8QxcV4sj77Jaa2M5
4baRrpRwy+kzoAsKz1tyZgdxph+D82QS37kN5beNgGP9WKekz3luSUem1X0GGA2+
SWoH0vt9s0ja9o6tx2KsvnDvmUDGftzBPctYdPSwRNgzrQDIA9p1WDYp5k1xX0Ce
yNz1hgZ14tvXjMJisPkob9x+HeaXMEq/gGQfdxrX6EqdoqrdxvqU3XxhzVby3dZ6
jl2RjH/GunoTQR5GimQOecJwa8/Um9FB3Qp6Vq1SY39ytrpSdpSTWNUCAwEAAaNT
MFEwHQYDVR0OBBYEFL2yQJFoVBTLuokdrIzcxJlJhP9DMB8GA1UdIwQYMBaAFL2y
QJFoVBTLuokdrIzcxJlJhP9DMA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZIhvcNAQEL
BQADggEBAHNWhVuDtuqyY3m2SOR8+1I7Njf7FiQkjqZwsWh1OUvAoA4/IaF5KTZ7
dxbXadocc0QvLxzZ4VUtnLvv/wkS6O10c8fqGwmo5iGs1trPxxl/ITGudZe5MnW7
3zLBAz+fjihpsmcobueD+GpUZGC1yCaRxe+xhJUJGNew1GIEJGbuqKD5/XSOMotv
FLLwRncvJkKNmRP5b1Sl7ishZOQH4f93tDISXgM+nRdzTKBlhKPyV3J/VW7T+wsv
AO0moNMiN/MnwXWhaJV3NaO9qeCssDksPmhxZvtJmL/u1EOjIVZJm1cPoGwPI5at
p6L3yvxnuNZ/zDHSx3xpX794fL/LI1Q=
-----END CERTIFICATE-----`;

// Signing is done server-side — the private key never leaves the backend.
// The frontend calls /api/qz/sign with the challenge string and gets back
// the RSA-SHA256 signature. Requires the user to be logged in.
async function signData(toSign: string): Promise<string> {
  const { default: api } = await import("./api");
  const res = await api.post<{ signature: string }>("/api/qz/sign", { message: toSign });
  return res.data.signature;
}

// ── QZ module cache ──

let qzCache: any = null;
async function getQz(): Promise<any> {
  if (qzCache) return qzCache;
  // @ts-ignore: no types available
  const mod = await import("qz-tray");
  qzCache = (mod as any).default ?? mod;
  return qzCache;
}

function applyDemoSecurity(qz: any) {
  qz.security.setCertificatePromise((_resolve: any, _reject: any) => {
    _resolve(DEMO_CERT);
  });
  qz.security.setSignaturePromise(async (toSign: any) => signData(toSign));
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
 * Connect to QZ Tray. Returns true if connected, false if QZ Tray is not running.
 */
export async function qzConnect(): Promise<boolean> {
  try {
    const qz = await getQz();
    if (qz.websocket.isActive()) return true;
    applyDemoSecurity(qz);
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
    const result = await qz.printers.find();
    if (!result) return [];
    return Array.isArray(result) ? result : [result];
  } catch {
    return [];
  }
}

/**
 * Print a full HTML document directly to the named printer via QZ Tray.
 */
export async function qzPrint(
  printerName: string,
  html: string,
  widthMm: number,
): Promise<void> {
  const qz = await getQz();
  if (!qz.websocket.isActive()) {
    applyDemoSecurity(qz);
    await qz.websocket.connect({ retries: 1, delay: 0.5 });
  }

  const config = qz.configs.create(printerName, {
    colorType: "blackWhite",
    size: { width: widthMm, height: null },
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
