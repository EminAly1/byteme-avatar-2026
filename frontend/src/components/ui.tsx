import {
  Children,
  Fragment,
  isValidElement,
  cloneElement,
  type ReactNode,
  type ReactElement,
} from "react";
import { AlertCircle, Check, PackageOpen } from "lucide-react";
import { ApiError } from "../lib/api";
import { useMediaQuery } from "../hooks/useMediaQuery";
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
      <PackageOpen size={26} />
      <p>{children}</p>
    </div>
  );
}
export function ErrorBox({ error }: { error: unknown }) {
  return (
    <div className="notice danger" role="alert">
      <AlertCircle size={19} />
      <div>
        <strong>İşlem tamamlanamadı</strong>
        <p>
          {error instanceof ApiError
            ? error.message
            : "Kayıtlar alınamadı. Bağlantıyı kontrol edip yeniden deneyin."}
        </p>
        {error instanceof ApiError && error.code && (
          <details className="support-details">
            <summary>Destek ayrıntısı</summary>
            <code>{error.code}</code>
          </details>
        )}
      </div>
    </div>
  );
}
export function LoadingSkeleton() {
  return (
    <div className="loading-state" role="status">
      <span>Kayıtlar yükleniyor…</span>
      <div className="skeleton-group" aria-hidden="true">
        <i />
        <i />
        <i />
      </div>
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
    <LoadingSkeleton />
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
type Cell = ReactElement<{ children?: ReactNode; className?: string }>;
function flatten(
  children: ReactNode,
): ReactElement<{ children?: ReactNode }>[] {
  return Children.toArray(children).flatMap((child) => {
    if (!isValidElement<{ children?: ReactNode }>(child)) return [];
    return child.type === Fragment ? flatten(child.props.children) : [child];
  });
}
const numeric = (header: string) =>
  /miktar|\bkg\b|tutar|maliyet|ekp|bakiye|kullanılabilir|tahmin|gerçekleş|sapma|mae|rmse/i.test(
    header,
  );
export function Table({
  headers,
  children,
  empty = false,
}: {
  headers: string[];
  children: ReactNode;
  empty?: boolean;
}) {
  const mobile = useMediaQuery("(max-width: 600px)");
  if (empty) return <Empty />;
  const rows = flatten(children);
  if (mobile)
    return (
      <div
        className="data-cards"
        aria-label={headers.join(", ") + " kayıtları"}
      >
        {rows.map((row, index) => {
          const cells = flatten(row.props.children) as Cell[];
          return (
            <article className="data-card" key={row.key ?? index}>
              <div className="data-card-title">{cells[0]?.props.children}</div>
              <dl>
                {cells.slice(1).map((cell, i) => (
                  <div
                    key={i}
                    className={numeric(headers[i + 1] || "") ? "numeric" : ""}
                  >
                    <dt>{headers[i + 1]}</dt>
                    <dd>{cell.props.children}</dd>
                  </div>
                ))}
              </dl>
            </article>
          );
        })}
      </div>
    );
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label={headers.join(", ") + " tablosu"}
    >
      <table>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h} className={numeric(h) ? "numeric" : ""}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) =>
            cloneElement(
              row,
              {},
              flatten(row.props.children).map((cell, i) =>
                cloneElement(cell as Cell, {
                  key: cell.key ?? i,
                  className:
                    ((cell.props as { className?: string }).className || "") +
                    (numeric(headers[i] || "") ? " numeric" : ""),
                }),
              ),
            ),
          )}
        </tbody>
      </table>
    </div>
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
