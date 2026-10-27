export const units = { kg: "kg", package: "paket", unit: "adet" };
export const productTypes = {
  raw: "Hammadde",
  finished: "Mamul",
  byproduct: "Yan ürün",
};
export const roles = {
  supplier: "Tedarikçi",
  producer: "Dış üretici",
  customer: "Müşteri",
};
export const locationKinds = {
  warehouse: "İşletme deposu",
  external_producer: "Üretici konumu",
  quarantine: "Karantina",
};
export const movementTypes: Record<string, string> = {
  receipt: "Alış girişi",
  transfer_out: "Depo transfer çıkışı", transfer_in: "Depo transfer kabulü",
  customer_return: "Müşteri iadesi · karantina", sale_cancellation: "Satış iptali ters hareketi",
  cancel_hold_out: "İptal karantina çıkışı", cancel_hold_in: "İptal karantina kabulü",
  rework_input: "Rework tüketimi", rework_output: "Rework yeni lot kabulü",
  dispatch_out: "Üreticiye sevk",
  dispatch_in: "Üreticide kabul",
  production_input: "Üretim tüketimi",
  production_output: "Mamul kabulü",
  return_out: "Üreticiden iade",
  return_in: "İade kabulü",
};
export const decimal = (s: string) => s.trim().replace(",", ".");
export const positive = (s: string) => !s.startsWith("-") && /[1-9]/.test(s);
// Display only: group decimal strings without a binary float or a cost calculation.
export function amount(value: string | null | undefined, fixed?: number) {
  if (value == null) return "—";
  const [whole, fraction = ""] = value.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const digits =
    fixed == null
      ? fraction.replace(/0+$/, "")
      : fraction.padEnd(fixed, "0").slice(0, fixed);
  return grouped + (digits ? "," + digits : "");
}
export const eur = (value: string | undefined) =>
  value == null
    ? "—"
    : amount(
        value,
        (value.split(".")[1] || "").replace(/0+$/, "").length > 2
          ? undefined
          : 2,
      ) + " €";
export const dateTime = (s: string) =>
  new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Istanbul",
  }).format(new Date(s));
export const short = (id: string) => id.slice(0, 8);
