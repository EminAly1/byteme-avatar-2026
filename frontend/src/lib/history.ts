// References to real server records only. No credentials or fabricated server-wide history.
export interface SavedRef {
  id: string;
  at: string;
  label: string;
}
export function readHistory(kind: "predictions" | "recalls"): SavedRef[] {
  try {
    const value = JSON.parse(
      sessionStorage.getItem("avatar.references:" + kind) || "[]",
    );
    return Array.isArray(value)
      ? value
          .filter(
            (x: SavedRef) =>
              typeof x.id === "string" &&
              /^[0-9a-f-]{36}$/.test(x.id) &&
              typeof x.at === "string" &&
              typeof x.label === "string",
          )
          .slice(0, 50)
      : [];
  } catch {
    return [];
  }
}
export function remember(kind: "predictions" | "recalls", value: SavedRef) {
  try {
    sessionStorage.setItem(
      "avatar.references:" + kind,
      JSON.stringify(
        [value, ...readHistory(kind).filter((x) => x.id !== value.id)].slice(
          0,
          50,
        ),
      ),
    );
  } catch {
    /* The returned server UUID remains available without browser storage. */
  }
}
