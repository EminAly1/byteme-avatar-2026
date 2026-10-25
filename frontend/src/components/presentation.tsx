import { useState, type ReactNode } from "react";
import {
  Copy,
  Check,
  PackageCheck,
  ArrowRight,
  CircleCheck,
  ShieldAlert,
} from "lucide-react";
import { Badge } from "./ui";
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
export function RecordId({
  label = "Kayıt referansı",
  id,
}: {
  label?: string;
  id: string;
}) {
  const [message, setMessage] = useState("");
  const readable = label
    .replace(/UUID/gi, "kaydı")
    .replace("Kayıt kimliği", "Kayıt referansı");
  return (
    <details className="record-reference">
      <summary>
        {readable} <span>Teknik referans</span>
      </summary>
      <div className="record-id">
        <code>{id}</code>
        <button
          className="icon-button"
          type="button"
          aria-label={readable + " kimliğini kopyala"}
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(id);
              setMessage("Kopyalandı");
            } catch {
              setMessage(
                "Panoya erişilemedi. Kodu seçerek kopyalayabilirsiniz.",
              );
            }
          }}
        >
          {message === "Kopyalandı" ? <Check size={16} /> : <Copy size={16} />}
        </button>
      </div>
      {message && (
        <p className="caption" role="status">
          {message}
        </p>
      )}
    </details>
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
        <li
          key={s}
          className={i < current ? "complete" : i === current ? "current" : ""}
          aria-current={i === current ? "step" : undefined}
        >
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
