import type { Command } from "./api";
export interface Pending {
  command: Command;
  values: Record<string, unknown>;
}
const prefix = "avatar.pending:";
// Idempotency metadata/form inputs only. Never store X-API-Key here.
export function loadPending(path: string): Pending | null {
  try {
    const v = JSON.parse(sessionStorage.getItem(prefix + path) || "null");
    return v?.command?.path === path &&
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
    sessionStorage.setItem(prefix + value.command.path, JSON.stringify(value));
  } catch {
    /* Memory retry still works if browser storage is disabled. */
  }
}
export function clearPending(path: string) {
  try {
    sessionStorage.removeItem(prefix + path);
  } catch {
    /* No credential is stored. */
  }
}
