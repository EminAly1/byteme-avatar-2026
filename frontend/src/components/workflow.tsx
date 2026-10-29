import type { ReactNode } from "react";
import {
  ArrowRight,
  CircleCheck,
  Filter,
} from "lucide-react";
import { useFormContext } from "react-hook-form";
import { Link } from "react-router-dom";
import { Field } from "./forms";
import { Badge, Empty, ErrorBox } from "./ui";
import { amount, positive, short, units } from "../lib/format";
import type { Location, Lot, Product, Stock } from "../lib/types";

export { PageHeader, StatCard } from "./presentation";
export function StatusBadge({
  status,
}: {
  status: "draft" | "posted" | "blocked" | "available";
}) {
  const labels = {
    draft: "Taslak",
    posted: "Tamamlandı",
    blocked: "Bloke",
    available: "Kullanılabilir",
  };
  return (
    <Badge
      tone={
        status === "blocked" ? "red" : status === "draft" ? "amber" : "green"
      }
    >
      {labels[status]}
    </Badge>
  );
}
export function FilterBar({ children }: { children: ReactNode }) {
  return (
    <div className="filters filter-bar">
      <Filter size={17} aria-hidden="true" />
      {children}
    </div>
  );
}
export const EmptyState = Empty;
export const ErrorState = ErrorBox;
export { LoadingSkeleton } from "./ui";
export function ToastNotification({ children }: { children: ReactNode }) {
  return (
    <div className="notice success" role="status">
      <CircleCheck size={20} />
      <span>{children}</span>
    </div>
  );
}
export { ConfirmDialog, DetailDrawer } from "./dialogs";
export const FormField = Field;
export function NumberInput(props: {
  name: string;
  label: string;
  hint?: string;
  placeholder?: string;
}) {
  return <Field {...props} type="decimal" />;
}
export function LotSelector({
  name,
  label,
  stocks,
  lots,
  products,
  locations,
  productId,
}: {
  name: string;
  label: string;
  stocks: Stock[];
  lots: Lot[];
  products: Product[];
  locations: Location[];
  productId?: string;
}) {
  const { watch } = useFormContext();
  const selected = watch(name) as string | undefined;
  const records = stocks.filter(
    (s) =>
      (!productId || s.product_id === productId) &&
      locations.find((l) => l.id === s.location_id)?.kind === "warehouse" &&
      positive(s.quantity),
  );
  const unavailable = records.find(
    (s) =>
      selected === s.lot_id + "|" + s.location_id &&
      (!positive(s.available_quantity) || s.blocked),
  );
  return (
    <>
      <Field name={name} label={label}>
        <option value="">Lot / konum seçin</option>
        {records.map((s) => {
          const lot = lots.find((l) => l.id === s.lot_id),
            product = products.find((p) => p.id === s.product_id),
            disabled = s.blocked || !positive(s.available_quantity);
          return (
            <option
              key={s.lot_id + s.location_id}
              value={s.lot_id + "|" + s.location_id}
              disabled={disabled}
            >
              {lot?.external_code} · {product?.name} ·{" "}
              {locations.find((l) => l.id === s.location_id)?.name} ·{" "}
              {amount(s.available_quantity)}{" "}
              {product && units[product.base_unit]}
              {disabled ? " — Bloke / tarihi geçmiş / kullanılamaz" : ""}
            </option>
          );
        })}
      </Field>
      {unavailable && (
        <p className="field-error" role="alert">
          Bu lot artık kullanılamıyor. Başka uygun lot seçin; backend durumu
          tekrar kontrol eder.
        </p>
      )}
    </>
  );
}
export {
  RecordId,
  ProcessSteps,
  ModuleIntro,
  ReviewSummary,
  CriticalNotice,
} from "./presentation";
export function LotLink({ id, code }: { id: string; code?: string }) {
  return (
    <Link className="text-button code" to={"/izlenebilirlik?lot=" + id}>
      {code || short(id)} <ArrowRight size={13} />
    </Link>
  );
}
