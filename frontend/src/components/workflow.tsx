import { useEffect, useId, useRef, type ReactNode, type KeyboardEvent } from "react";
import {
  ArrowRight,
  CircleCheck,
  Filter,
  X,
  PackageCheck,
  ShieldAlert,
} from "lucide-react";
import { useFormContext } from "react-hook-form";
import { Link } from "react-router-dom";
import { Field } from "./forms";
import { Badge, Empty, ErrorBox } from "./ui";
import { amount, positive, short, units } from "../lib/format";
import type { Location, Lot, Product, Stock } from "../lib/types";

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">BYTEME / OPERASYON MERKEZİ</p>
        <h1>{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {action}
    </div>
  );
}
export function StatCard({
  label,
  value,
  note,
  icon,
}: {
  label: string;
  value: ReactNode;
  note?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="stat">
      <div className="stat-top">
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </div>
  );
}
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
export function LoadingSkeleton() {
  return (
    <div
      className="skeleton-group"
      role="status"
      aria-label="Kayıtlar yükleniyor"
    >
      <span />
      <span />
      <span />
    </div>
  );
}
export function ToastNotification({ children }: { children: ReactNode }) {
  return (
    <div className="notice success" role="status">
      <CircleCheck size={20} />
      <span>{children}</span>
    </div>
  );
}
// Keep Tab navigation inside the modal instead of visiting browser chrome at the boundary.
function containDialogFocus(event: KeyboardEvent<HTMLDialogElement>) {
  if (event.key !== 'Tab') return;
  const candidates = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button, a[href], input, select, textarea, [tabindex]'))
    .filter(el => el.tabIndex >= 0 && !el.hasAttribute('disabled') && el.getClientRects().length > 0);
  const first = candidates[0], last = candidates[candidates.length - 1];
  if (!first || !last) return;
  if (event.shiftKey && document.activeElement === first) {event.preventDefault();last.focus();}
  else if (!event.shiftKey && document.activeElement === last) {event.preventDefault();first.focus();}
}
export function ConfirmDialog({
  title = "İşlemi onaylayın",
  children,
  onCancel,
  onConfirm,
}: {
  title?: string;
  children: ReactNode;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null),
    id = useId();
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => {
      if (dialog?.open && dialog.isConnected) dialog.close();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby={id}
      onKeyDown={containDialogFocus}
      onCancel={(e) => {
        e.preventDefault();
        ref.current?.close();
        onCancel();
      }}
    >
      <h2 id={id}>{title}</h2>
      {children}
      <div className="actions">
        <button
          type="button"
          autoFocus
          className="button"
          onClick={() => {
            ref.current?.close();
            onCancel();
          }}
        >
          Vazgeç
        </button>
        <button
          type="button"
          className="button primary"
          onClick={() => {
            ref.current?.close();
            onConfirm();
          }}
        >
          Onayla ve kaydet
        </button>
      </div>
    </dialog>
  );
}
export function DetailDrawer({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null),
    id = useId();
  useEffect(() => {
    const el = ref.current;
    el?.showModal();
    return () => {
      if (el?.open && el.isConnected) el.close();
    };
  }, []);
  return (
    <dialog
      className="detail-drawer"
      ref={ref}
      aria-labelledby={id}
      onKeyDown={containDialogFocus}
      onCancel={(e) => {
        e.preventDefault();
        ref.current?.close();
        onClose();
      }}
    >
      <div className="section-head">
        <h2 id={id}>{title}</h2>
        <button
          className="icon-button"
          autoFocus
          onClick={() => {
            ref.current?.close();
            onClose();
          }}
          aria-label="Ayrıntıyı kapat"
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export const FormField = Field;
export function NumberInput(props: {
  name: string;
  label: string;
  hint?: string;
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
export function RecordId({
  label = "Kayıt kimliği",
  id,
}: {
  label?: string;
  id: string;
}) {
  return (
    <div className="record-id">
      <span>{label}</span>
      <code>{id}</code>
    </div>
  );
}
export function ProcessSteps({
  steps,
  current,
}: {
  steps: string[];
  current: number;
}) {
  return (
    <ol className="process-steps" aria-label="İşlem adımları">
      {steps.map((s, i) => (
        <li key={s} className={i <= current ? "complete" : ""}>
          <span>{i < current ? <CircleCheck size={15} /> : i + 1}</span>
          {s}
          {i < steps.length - 1 && <ArrowRight size={14} />}
        </li>
      ))}
    </ol>
  );
}
export function ModuleIntro({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon?: ReactNode;
}) {
  return (
    <div className="module-intro">
      <div className="module-glyph">{icon || <PackageCheck size={24} />}</div>
      <div>
        <span className="eyebrow">KAYITLI OPERASYON</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  );
}
export function ReviewSummary({
  items,
}: {
  items: Array<[string, ReactNode]>;
}) {
  return (
    <dl className="review-summary">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
export function CriticalNotice({ children }: { children: ReactNode }) {
  return (
    <div className="notice warning">
      <ShieldAlert size={19} />
      <span>{children}</span>
    </div>
  );
}
export function LotLink({ id, code }: { id: string; code?: string }) {
  return (
    <Link className="text-button code" to={"/izlenebilirlik?lot=" + id}>
      {code || short(id)} <ArrowRight size={13} />
    </Link>
  );
}
