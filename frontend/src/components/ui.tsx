import type { ReactNode } from "react";
import { AlertCircle, LoaderCircle, Check, PackageOpen } from "lucide-react";
import { ApiError } from "../lib/api";

export function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
export function Empty({
  children = "Henüz kayıt bulunmuyor.",
}: {
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <PackageOpen size={28} />
      <p>{children}</p>
    </div>
  );
}
export function ErrorBox({ error }: { error: unknown }) {
  return (
    <div className="notice danger" role="alert">
      <AlertCircle size={19} />
      <span>
        {error instanceof ApiError
          ? error.message
          : "Veriler alınamadı. Bağlantıyı kontrol edip sayfayı yenileyin."}
      </span>
    </div>
  );
}
export function State({
  loading,
  error,
  children,
}: {
  loading: boolean;
  error?: unknown;
  children: ReactNode;
}) {
  return error ? (
    <ErrorBox error={error} />
  ) : loading ? (
    <div className="empty" role="status">
      <LoaderCircle className="spin" />
      Kayıtlar yükleniyor…
    </div>
  ) : (
    <>{children}</>
  );
}
export function Section({
  title,
  subtitle,
  children,
  action,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="section-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Table({
  headers,
  children,
  empty = false,
}: {
  headers: string[];
  children: ReactNode;
  empty?: boolean;
}) {
  return empty ? (
    <Empty />
  ) : (
    <>
      <div
        className="table-scroll"
        tabIndex={0}
        role="region"
        aria-label={headers.join(", ") + " tablosu"}
      >
        <table>
          <thead>
            <tr>
              {headers.map((x) => (
                <th key={x}>{x}</th>
              ))}
            </tr>
          </thead>
          <tbody>{children}</tbody>
        </table>
      </div>
      <p className="scroll-hint">Diğer sütunlar için tabloyu yatay kaydırın.</p>
    </>
  );
}
export function Success({ children }: { children: ReactNode }) {
  return (
    <div className="notice success" role="status">
      <Check size={19} />
      <span>{children}</span>
    </div>
  );
}
