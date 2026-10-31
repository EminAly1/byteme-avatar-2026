import type { Command } from "./api";
export interface Pending {
  command: Command;
  values: Record<string, unknown>;
}
const prefix = "avatar.pending:";
// Idempotency metadata/form inputs only. Never store X-API-Key here.
const storageKey = (path: string, method = "POST") => prefix + (method === "POST" ? path : method + ":" + path);
export function loadPending(path: string, method = "POST"): Pending | null {
  try {
    const v = JSON.parse(sessionStorage.getItem(storageKey(path, method)) || "null");
    return v?.command?.path === path && (v.command.method || "POST") === method &&
      typeof v.command.key === "string" &&
      /^[0-9a-f-]{36}$/.test(v.command.key) &&
      v.command.body &&
      v.values
      ? v
      : null;
  } catch {
    return null;
  }
}
export function savePending(value: Pending) {
  try {
    sessionStorage.setItem(storageKey(value.command.path, value.command.method), JSON.stringify(value));
  } catch {
    /* Memory retry still works if browser storage is disabled. */
  }
}
export function clearPending(path: string, method = "POST") {
  try {
    sessionStorage.removeItem(storageKey(path, method));
  } catch {
    /* No credential is stored. */
  }
}
