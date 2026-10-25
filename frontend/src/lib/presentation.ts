import { amount } from "./format";

/** Display rounding only. Source strings and all request payloads remain untouched. */
export function displayDecimal(
  value: string | null | undefined,
  places = 3,
  minPlaces = 0,
): string {
  if (value == null) return "—";
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value);
  if (!match) return value;
  const [, sign, whole, fraction = ""] = match;
  let scaled = BigInt(whole + fraction.padEnd(places, "0").slice(0, places));
  if ((fraction[places] || "0") >= "5") scaled += 1n;
  const raw = scaled.toString().padStart(places + 1, "0");
  const integer = places ? raw.slice(0, -places) : raw;
  const decimals = places
    ? raw.slice(-places).replace(/0+$/, "").padEnd(minPlaces, "0")
    : "";
  return amount(
    (sign && scaled !== 0n ? "-" : "") +
      integer +
      (decimals ? "." + decimals : ""),
    decimals ? Math.max(minPlaces, decimals.length) : undefined,
  );
}
export const displayEuro = (value: string | null | undefined) =>
  value == null ? "—" : displayDecimal(value, 2, 2) + " €";
export function displayYield(value: string | null | undefined) {
  if (value == null) return "—";
  // Decimal shift for a percentage presentation; never changes the stored kg/kg ratio.
  const m = /^(\d+)(?:\.(\d+))?$/.exec(value);
  if (!m) return value;
  const digits = (m[2] || "").padEnd(2, "0");
  return (
    displayDecimal(
      (BigInt(m[1]) * 100n + BigInt(digits.slice(0, 2))).toString() +
        "." +
        (digits.slice(2) || "0"),
      2,
    ) + "%"
  );
}
