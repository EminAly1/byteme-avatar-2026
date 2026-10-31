// Capabilities live only in this open dialog's memory, never browser storage.
export type ShareStatus =
  | { state: "active"; url: string; expiresAt: number; version: string; bytes: number; sha256: string }
  | { state: "inactive" | "used" | "expired" | "local_only" | "unavailable" };

export function privateIpv4(host: string): boolean {
  const parts = host.split(".");
  if (parts.length !== 4 || parts.some((p) => !/^(0|[1-9]\d{0,2})$/.test(p) || +p > 255)) return false;
  const [a, b] = parts.map(Number);
  return a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168);
}

export function parseShareStatus(value: unknown, now = Date.now()): ShareStatus {
  if (!value || typeof value !== "object") throw new Error("Geçersiz paylaşım durumu.");
  const s = value as Record<string, unknown>;
  if (["inactive", "used", "expired", "local_only", "unavailable"].includes(String(s.state)))
    return { state: s.state as Exclude<ShareStatus["state"], "active"> };
  if (s.state !== "active" || typeof s.url !== "string") throw new Error("Geçersiz paylaşım durumu.");
  const u = new URL(s.url);
  if (u.protocol !== "http:" || !privateIpv4(u.hostname) || !u.port || u.username || u.password || u.search || u.hash ||
    !/^\/download\/[A-Za-z0-9_-]{43}$/.test(u.pathname) || u.href !== s.url ||
    typeof s.expiresAt !== "number" || !Number.isFinite(s.expiresAt) || s.expiresAt > now + 601_000 ||
    typeof s.bytes !== "number" || !Number.isSafeInteger(s.bytes) || s.bytes <= 0 || s.bytes > 128 * 1024 * 1024 ||
    typeof s.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(s.sha256) ||
    typeof s.version !== "string" || !/^[a-zA-Z0-9._+-]{1,80}$/.test(s.version))
    throw new Error("Paylaşım güvenli biçimde doğrulanamadı.");
  if (s.expiresAt <= now) return { state: "expired" };
  return { state: "active", url: s.url, expiresAt: s.expiresAt, version: s.version, bytes: s.bytes, sha256: s.sha256 };
}

export async function fetchShareStatus(signal?: AbortSignal): Promise<ShareStatus> {
  const response = await fetch("/api/apk-share", {
    headers: { "X-Avatar-Apk-Status": "1" }, cache: "no-store", credentials: "same-origin", signal,
  });
  if (!response.ok) throw new Error("Yerel APK paylaşımına erişilemiyor. Aracı ve web bağlantısını kontrol edin.");
  try { return parseShareStatus(await response.json()); }
  catch { throw new Error("Yerel APK paylaşımına erişilemiyor. Aracı ve web bağlantısını kontrol edin."); }
}
