import { useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Download,
  FileText,
  Printer,
  ArrowLeft,
  ShieldCheck,
  Eye,
  Pencil,
} from "lucide-react";
import { request } from "../lib/api";
import { dateTime, eur } from "../lib/format";
import type { Page } from "../lib/types";
import type { Sale } from "../lib/modules";
import {
  draftLimits,
  fetchDocumentPdf,
  initialDraft,
  saveDocumentPdf,
  type DraftFields,
  type DocumentKind,
  type DocumentSource,
} from "../lib/documents";
import { Empty, ErrorBox, Section, State } from "../components/ui";
import { ModuleIntro } from "../components/workflow";
import { DocumentSheet } from "../components/DocumentSheet";
import { PdfPreview } from "../components/PdfPreview";
import { inputPlaceholder } from "../lib/input-examples";
import "./documents.css";

function useSource(id: string) {
  return useQuery({
    queryKey: ["document-source", id],
    queryFn: () => request<DocumentSource>("/document-drafts/sales/" + id),
    retry: false,
    refetchOnWindowFocus: false,
  });
}
function DocumentCard({ sale }: { sale: Sale }) {
  const q = useSource(sale.id),
    [busy, setBusy] = useState(""),
    [error, setError] = useState<unknown>(),
    [preview, setPreview] = useState<Blob>();
  const [draft] = useState(initialDraft);
  const previewOpener = useRef<HTMLElement | null>(null);
  async function output(mode: "preview" | "pdf") {
    if (!q.data) return;
    if (mode === "preview")
      previewOpener.current = document.activeElement as HTMLElement;
    setBusy(mode);
    setError(undefined);
    try {
      const blob = await fetchDocumentPdf(q.data, "proforma", draft);
      if (mode === "preview") setPreview(blob);
      else saveDocumentPdf(blob, sale.id, "proforma");
    } catch (err) {
      setPreview(undefined);
      setError(err);
    } finally {
      setBusy("");
    }
  }
  return (
    <article
      className="document-card"
      aria-label={q.data?.customer.name || "Satış belgesi"}
    >
      <div className="document-card-heading">
        <span className="document-card-icon">
          <FileText size={22} />
        </span>
        <div>
          <h3>{q.data?.customer.name || "Satış kaydı"}</h3>
          <p className="caption">{dateTime(sale.sold_at)}</p>
        </div>
        {q.data && <span className="badge">{q.data.state_label}</span>}
      </div>
      <State loading={q.isPending} error={q.error}>
        {q.data && (
          <>
            <p className="document-card-lots">
              {q.data.lines
                .slice(0, 2)
                .map((l) => l.lot_code)
                .join(" · ")}
              {q.data.lines.length > 2
                ? ` · +${q.data.lines.length - 2} kalem`
                : ""}
            </p>
            <div className="document-card-total">
              <span>Düzeltme sonrası kayıtlı tutar</span>
              <strong>{eur(q.data.net_after_adjustments_eur)}</strong>
            </div>
          </>
        )}
      </State>
      <div className="document-card-actions">
        <Link className="button primary" to={"/belgeler/satis/" + sale.id}>
          <Eye size={16} />
          Görüntüle
        </Link>
        <Link className="button" to={"/belgeler/satis/" + sale.id + "/duzenle"}>
          <Pencil size={16} />
          Taslak düzenle
        </Link>
        <button
          className="button"
          disabled={!q.data || !!busy}
          onClick={() => void output("pdf")}
        >
          <Download size={16} />
          {busy === "pdf" ? "Hazırlanıyor…" : "PDF indir"}
        </button>
        <button
          className="button"
          disabled={!q.data || !!busy}
          onClick={() => void output("preview")}
        >
          <Eye size={16} />
          {busy === "preview" ? "Hazırlanıyor…" : "Önizle"}
        </button>
        <button className="button" disabled title="Belge kesin satıştan üretilir; kaynak satış veya mali geçmiş bu ekrandan silinemez.">Sil</button>
      </div>
      <p className="caption">Düzenleme yalnız geçici belge notlarını etkiler; kesin satış ve geçmiş silinmez.</p>
      {error ? <ErrorBox error={error} /> : null}
      {preview && q.data && (
        <PdfPreview
          blob={preview}
          returnFocus={previewOpener.current || undefined}
          onClose={() => setPreview(undefined)}
          busy={!!busy}
          onDownload={() => void output("pdf")}
        >
          <DocumentSheet source={q.data} kind="proforma" draft={draft} />
        </PdfPreview>
      )}
    </article>
  );
}
export function Documents() {
  const [cursor, setCursor] = useState("");
  const q = useQuery({
    queryKey: ["document-sales", cursor],
    queryFn: () =>
      request<Page<Sale>>(
        "/sales?limit=20" + (cursor ? "&cursor=" + cursor : ""),
      ),
    retry: false,
  });
  return (
    <div className="stack document-root">
      <ModuleIntro
        title="Kesin kayıttan, özenli belgeye."
        description="Bir satış seçin; belgeyi görüntüleyin veya geçici notlarını düzenleyin. Önizleme ve indirme, gerçek PDF dosyasını kullanır."
        icon={<FileText size={24} />}
      />
      <div className="document-boundary">
        <ShieldCheck size={20} />
        <div>
          <strong>Belge taslağı, kesin satıştan ayrı.</strong>
          <p>
            Fiyatlar, miktarlar ve lotlar kaynak kayıttan gelir. Proforma resmî
            fatura değildir. Taslak arşivi tutulmaz; satış silinmez.
          </p>
        </div>
      </div>
      <Section
        title="Belge için satış seçin"
        subtitle="Müşteri ve lot bilgileriyle en fazla 20 satış gösterilir. İade ve iptaller tutardan ayrı kayıtlardır."
      >
        <State loading={q.isPending} error={q.error}>
          {q.data && !q.data.items.length ? (
            <Empty>
              Henüz kayıtlı satış yok. Satış kaydı olmadan tutar veya belge
              uydurulmaz.{" "}
              <Link className="text-button" to="/satislar">
                Satışlara git
              </Link>
            </Empty>
          ) : (
            <div className="document-grid">
              {q.data?.items.map((s) => (
                <DocumentCard key={s.id} sale={s} />
              ))}
            </div>
          )}
          <div className="document-pagination">
            <button
              className="button"
              disabled={!cursor}
              onClick={() => setCursor("")}
            >
              İlk sayfa
            </button>
            <button
              className="button"
              disabled={!q.data?.next_cursor}
              onClick={() => setCursor(q.data?.next_cursor || "")}
            >
              Sonraki sayfa
            </button>
          </div>
        </State>
      </Section>
    </div>
  );
}
const fields = [
  ["title", "Belge başlığı"],
  ["description", "Belge açıklaması"],
  ["seller_name", "Satıcı unvanı"],
  ["seller_contact", "Satıcı iletişim bilgisi"],
  ["reference", "Taslak referansı"],
  ["payment_note", "Ödeme / vade açıklaması"],
  ["delivery_note", "Teslimat açıklaması"],
  ["note", "Özel not"],
] as const;
function Editor({ saleId }: { saleId: string }) {
  const q = useSource(saleId),
    navigate = useNavigate(),
    location = useLocation();
  const editing = location.pathname.endsWith("/duzenle"),
    base = "/belgeler/satis/" + saleId;
  const [applied, setApplied] = useState(initialDraft),
    [draft, setDraft] = useState(initialDraft),
    [kind, setKind] = useState<DocumentKind>("proforma"),
    [appliedKind, setAppliedKind] = useState<DocumentKind>("proforma");
  const [busy, setBusy] = useState(""),
    [error, setError] = useState<unknown>(),
    [notice, setNotice] = useState(""),
    [preview, setPreview] = useState<Blob>();
  const form = useRef<HTMLFormElement>(null),
    previewOpener = useRef<HTMLElement | null>(null);
  async function output(mode: "pdf" | "print" | "preview") {
    if (!q.data) return;
    if (mode === "preview")
      previewOpener.current = document.activeElement as HTMLElement;
    setBusy(mode);
    setError(undefined);
    setNotice("");
    try {
      if (mode === "pdf" || mode === "preview") {
        const blob = await fetchDocumentPdf(q.data, appliedKind, applied);
        if (mode === "preview") setPreview(blob);
        else {
          saveDocumentPdf(blob, saleId, appliedKind);
          setNotice("PDF dosyası indirildi. Taslak sunucuda saklanmadı.");
        }
      } else {
        const fresh = await request<DocumentSource>(
          "/document-drafts/sales/" + saleId,
        );
        if (fresh.source_fingerprint !== q.data.source_fingerprint) {
          setPreview(undefined);
          await q.refetch();
          setNotice(
            "Kaynak değişti. Önizleme güncellendi; inceleyip yeniden yazdırın.",
          );
          return;
        }
        await document.fonts.ready;
        window.print();
      }
    } catch (err) {
      setPreview(undefined);
      setError(err);
    } finally {
      setBusy("");
    }
  }
  const sheet = q.data ? (
    <DocumentSheet source={q.data} kind={appliedKind} draft={applied} />
  ) : null;
  return (
    <div className="stack document-root">
      <div className="document-toolbar">
        <Link className="text-button" to="/belgeler">
          <ArrowLeft size={15} /> Belge merkezi
        </Link>
        <Link className="text-button" to={"/satislar/" + saleId}>
          Kaynak satışa dön
        </Link>
      </div>
      <State loading={q.isPending} error={q.error}>
        {q.data && (
          <>
            <div className="document-toolbar">
              <div>
                <h2>{q.data.customer.name}</h2>
                <p className="caption">
                  Geçici taslak — sunucuda saklanmıyor. Bu satışın belge
                  ekranından ayrılınca notlar sıfırlanır.
                </p>
              </div>
              {!editing && (
                <div className="document-actions">
                  <Link
                    className="button"
                    to={base + "/duzenle"}
                    onClick={() => {
                      setDraft({ ...applied });
                      setKind(appliedKind);
                      setNotice("");
                    }}
                  >
                    <Pencil size={17} />
                    Taslak düzenle
                  </Link>
                  <button
                    className="button"
                    disabled={!!busy}
                    onClick={() => void output("preview")}
                  >
                    <Eye size={17} />
                    {busy === "preview" ? "Hazırlanıyor…" : "Önizle"}
                  </button>
                  <button
                    className="button"
                    disabled={!!busy}
                    onClick={() => void output("print")}
                  >
                    <Printer size={17} />
                    {busy === "print" ? "Kaynak kontrol ediliyor…" : "Yazdır"}
                  </button>
                  <button
                    className="button primary"
                    disabled={!!busy}
                    onClick={() => void output("pdf")}
                  >
                    <Download size={17} />
                    {busy === "pdf" ? "PDF hazırlanıyor…" : "PDF indir"}
                  </button>
                </div>
              )}
            </div>
            {error ? (
              <div className="document-output-error">
                <ErrorBox error={error} />
                <button
                  className="button"
                  onClick={() => {
                    setPreview(undefined);
                    setError(undefined);
                    void q.refetch();
                  }}
                >
                  Önizlemeyi yenile
                </button>
              </div>
            ) : null}
            {notice && (
              <p className="notice" role="status">
                {notice}
              </p>
            )}
            {editing ? (
              <>
                <div className="document-boundary">
                  <ShieldCheck size={20} />
                  <div>
                    <strong>Kesin kayıtlar kilitli.</strong>
                    <p>
                      {q.data.customer.name} · {q.data.state_label} ·{" "}
                      {eur(q.data.net_after_adjustments_eur)}. Müşteri, fiyat,
                      miktar, lot ve muhasebe alanları bu formda değiştirilemez.
                    </p>
                  </div>
                </div>
                <aside
                  className="document-editor"
                  aria-label="Belge taslak ayarları"
                >
                  <Section
                    title="Taslak ayarları"
                    subtitle="Yalnız bu görünümde uygulanır; sunucuda veya tarayıcı arşivinde saklanmaz."
                  >
                    <form
                      ref={form}
                      className="stack"
                      onSubmit={(e) => {
                        e.preventDefault();
                        if (!form.current?.reportValidity()) return;
                        setApplied({ ...draft });
                        setAppliedKind(kind);
                        setNotice(
                          "Taslak bu görünümde uygulandı. Sunucuda saklanmadı.",
                        );
                        navigate(base);
                      }}
                    >
                      <div className="document-field-grid">
                        <label>
                          Belge görünümü
                          <select
                            aria-label="Belge görünümü"
                            value={kind}
                            onChange={(e) =>
                              setKind(e.target.value as DocumentKind)
                            }
                          >
                            <option value="proforma">Proforma taslağı</option>
                            <option value="sale_summary">Satış özeti</option>
                          </select>
                        </label>
                        <label>
                          Belge düzenleme tarihi
                          <input
                            type="date"
                            required
                            value={draft.document_date}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                document_date: e.target.value,
                              })
                            }
                          />
                        </label>
                        {fields.map(([name, label]) => (
                          <div className="field" key={name}>
                            <label htmlFor={"draft-" + name}>{label}</label>
                            {[
                              "description",
                              "seller_contact",
                              "payment_note",
                              "delivery_note",
                              "note",
                            ].includes(name) ? (
                              <textarea
                                id={"draft-" + name}
                                rows={name === "note" ? 4 : 2}
                                placeholder={inputPlaceholder(name, label)}
                                aria-describedby={"hint-" + name}
                                maxLength={draftLimits[name]}
                                value={draft[name]}
                                onChange={(e) => {
                                  e.target.setCustomValidity(
                                    e.target.value.split("\n").length > 21
                                      ? "En fazla 21 satır girin."
                                      : "",
                                  );
                                  setDraft({
                                    ...draft,
                                    [name]: e.target.value,
                                  });
                                }}
                              />
                            ) : (
                              <input
                                id={"draft-" + name}
                                placeholder={inputPlaceholder(name, label)}
                                aria-describedby={"hint-" + name}
                                maxLength={draftLimits[name]}
                                value={draft[name]}
                                onChange={(e) =>
                                  setDraft({ ...draft, [name]: e.target.value })
                                }
                              />
                            )}
                            <small id={"hint-" + name}>
                              İsteğe bağlı; en fazla {draftLimits[name]} karakter ve 21 satır.
                              {name.startsWith("seller")
                                ? " Kullanıcı girişi; doğrulanmadı."
                                : ""}
                            </small>
                          </div>
                        ))}
                      </div>
                      <label className="document-demo-toggle">
                        <input
                          type="checkbox"
                          checked={draft.demo}
                          onChange={(e) =>
                            setDraft({ ...draft, demo: e.target.checked })
                          }
                        />{" "}
                        Kurgusal demo belgesi (kullanıcı beyanı)
                      </label>
                      <div className="document-actions">
                        <Link
                          className="button"
                          to={base}
                          onClick={() => {
                            setDraft({ ...applied });
                            setKind(appliedKind);
                          }}
                        >
                          Vazgeç
                        </Link>
                        <button className="button primary" type="submit">
                          Değişiklikleri bu görünümde uygula
                        </button>
                      </div>
                    </form>
                  </Section>
                </aside>
              </>
            ) : (
              <section
                className="document-preview"
                aria-label="Belge önizleme alanı"
              >
                <div className="document-preview-caption">
                  <span>Salt okunur · A4 · EUR</span>
                  <span>Çok sayfalı dosya için Önizle seçin</span>
                </div>
                {sheet}
              </section>
            )}
            {preview && (
              <PdfPreview
                blob={preview}
                returnFocus={previewOpener.current || undefined}
                busy={!!busy}
                onClose={() => setPreview(undefined)}
                onDownload={() => void output("pdf")}
                onPrint={() => void output("print")}
              >
                {sheet}
              </PdfPreview>
            )}
          </>
        )}
      </State>
    </div>
  );
}
export function SaleDocument() {
  const { id = "" } = useParams();
  return <Editor key={id} saleId={id} />;
}
