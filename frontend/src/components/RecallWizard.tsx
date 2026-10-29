import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldAlert, ArrowRight, ArrowLeft, Check } from "lucide-react";
import { ApiError, newCommand, request, send, type Command } from "../lib/api";
import { clearPending, loadPending, savePending, type Pending } from "../lib/pending";
import { useCatalog } from "../lib/data";
import type { Recall, RecallPreview, RecallReviewCommand, TraceReport } from "../lib/modules";
import { amount, units } from "../lib/format";
import { Badge, Empty, ErrorBox, Section, State } from "./ui";
import { ConfirmDialog } from "./dialogs";
import { DistributionEvidence } from "./DistributionEvidence";
import "./recall.css";

const labels = ["Kaynak ve etki", "Gerekçe ve risk", "Kesin onay"];
const finalLabel = "Geri çağırmayı kesinleştir ve lotları bloke et";
function ImpactSummary({ report, compact = false }: { report: TraceReport; compact?: boolean }) {
  return <dl className={"recall-metrics" + (compact ? " recall-metrics-compact" : "")}>
    <div><dt>Etkilenen lot</dt><dd>{report.lots.length}</dd></div>
    <div><dt>Kayıtlı stok konumu</dt><dd>{new Set(report.stocks.map(s => s.location_id)).size}</dd></div>
    <div><dt>Birinci kademe alıcı</dt><dd>{report.buyers.length}</dd></div>
    <div><dt>Kayıtlı ikinci kademe alıcı</dt><dd>{new Set(report.second_tier_distributions.map(r => r.recipient_party_id)).size}</dd></div>
    <div><dt>Sevkiyat kaydı</dt><dd>{report.shipments.length}</dd></div>
  </dl>;
}
function Risk() {
  return <div className="recall-risk" role="note">
    <ShieldAlert aria-hidden="true" size={24} />
    <div><strong>Yüksek risk · Lot blokajı</strong>
      <p>Bu işlem satışları engelleyebilir ve mevcut sistemde otomatik blok kaldırma bulunmuyor.</p>
      <p>Kayıtlı alıcılara otomatik bildirim gönderilmez. İletişimi ayrıca yürütün.</p>
    </div>
  </div>;
}

export function RecallWizard({ onSuccess }: { onSuccess: (record: Recall) => void }) {
  const catalog = useCatalog(), client = useQueryClient();
  const [pending, setPending] = useState<Pending | null>(() => loadPending("/recalls"));
  const initial = pending?.command.body as { source_lot_id?: string; reason?: string } | undefined;
  const [lot, setLot] = useState(initial?.source_lot_id || "");
  const [reason, setReason] = useState(initial?.reason || "");
  const [step, setStep] = useState(pending ? 3 : 1);
  const [review, setReview] = useState<RecallPreview | null>(null);
  const [typedCode, setTypedCode] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const inFlight = useRef(false), heading = useRef<HTMLHeadingElement>(null);
  const reviewButton = useRef<HTMLButtonElement>(null), restoreFocus = useRef(false);
  const preview = useQuery({
    queryKey: ["recall-preview", lot],
    queryFn: () => request<RecallPreview>(`/recalls/preview?source_lot_id=${lot}`),
    enabled: !!lot && !pending && step === 1,
    retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false,
  });
  // Keep the impact the user actually reviewed. A global query invalidation
  // must never silently replace it with a new fingerprint halfway through.
  const report = step === 1 ? preview.data?.report : review?.report;
  const code = report?.source_lot.external_code || "";
  const ready = !!report && (step !== 1 || (!preview.isFetching && !preview.isError));
  const validReason = !!reason.trim() && reason.trim().length <= 500;
  useEffect(() => {
    if (showConfirm || pending) return;
    if (restoreFocus.current) { restoreFocus.current = false; reviewButton.current?.focus(); }
    else heading.current?.focus();
  }, [step, showConfirm, pending]);
  useEffect(() => {
    if (!pending) return;
    const warn = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [pending]);

  async function transmit(command: Command) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError(null);
    try {
      const result = await send<Recall>(command);
      clearPending("/recalls");
      void client.invalidateQueries();
      onSuccess(result);
    } catch (failure) {
      setError(failure);
      // A transport/5xx error may follow a committed transaction. Preserve the
      // original key AND reviewed body; never refresh/rekey an uncertain write.
      if (!(failure instanceof ApiError && failure.uncertain)) {
        clearPending("/recalls"); setPending(null); setStep(1); setReview(null); setTypedCode("");
        void client.invalidateQueries({ queryKey: ["recall-preview", lot] });
      }
    } finally {
      inFlight.current = false; setBusy(false);
    }
  }
  function finalize() {
    if (!ready || !validReason || typedCode !== code || inFlight.current || pending) return;
    const body: RecallReviewCommand = {
      source_lot_id: lot, reason: reason.trim(),
      preview_fingerprint: review!.preview_fingerprint,
      confirmation_lot_code: typedCode,
    };
    const command = newCommand("/recalls", body);
    const saved: Pending = { command, values: {
      source_lot_id: lot, reason: reason.trim(), source_code: code,
      lot_count: report!.lots.length,
      location_count: new Set(report!.stocks.map(s => s.location_id)).size,
      buyer_count: report!.buyers.length,
      second_tier_count: new Set(report!.second_tier_distributions.map(r => r.recipient_party_id)).size,
    } };
    savePending(saved); setPending(saved); setShowConfirm(false);
    void transmit(command);
  }
  return <Section title="Geri çağırma kaydı aç" subtitle="Kaynağı inceleyin, riski değerlendirin ve lot koduyla kesin onay verin.">
    <div className="recall-wizard" aria-busy={busy}>
      <ol className="recall-steps" aria-label="Geri çağırma aşamaları">
        {labels.map((label, i) => <li key={label} aria-current={step === i + 1 ? "step" : undefined}>
          <span aria-hidden="true">{step > i + 1 ? <Check size={16} /> : i + 1}</span><strong>{label}</strong>
        </li>)}
      </ol>
      {error != null && <ErrorBox error={error} />}
      {pending ? <div className="stack">
        <Risk />
        <h3>{busy ? "Kesinleştiriliyor…" : "İşlemin sonucu henüz doğrulanamadı"}</h3>
        <p role="status">{busy ? "Backend yanıtı bekleniyor. Aynı işlem tekrar başlatılamaz." : "İstek kaydedilmiş olabilir. Kaynak ve gerekçe korunuyor; aynı anahtar ve içerikle sonucu güvenle sorgulayın."}</p>
        <p><strong>Kaynak: {String(pending.values.source_code || catalog.lots.find(l => l.id === lot)?.external_code || "Kaydedilmiş kaynak lot")}</strong></p>
        <p>Gerekçe: {String((pending.command.body as { reason: string }).reason)}</p>
        {pending.values.lot_count != null && <p>Onay anındaki özet: {String(pending.values.lot_count)} lot · {String(pending.values.location_count)} konum · {String(pending.values.buyer_count)} ilk kademe ve {String(pending.values.second_tier_count)} ikinci kademe alıcı. Güncel sonuç backend yanıtıyla doğrulanır.</p>}
        <button type="button" className="button danger" disabled={busy} onClick={() => void transmit(pending.command)}>
          {busy ? "Yanıt bekleniyor…" : "Aynı işlemi tekrar dene"}
        </button>
      </div> : <>
        <h3 ref={heading} tabIndex={-1}>Aşama {step} · {labels[step - 1]}</h3>
        {step === 1 && <>
          <State loading={catalog.loading} error={catalog.error}>
            <label className="field">Sorunlu kaynak lot
              <select aria-label="Sorunlu kaynak lot" value={lot} onChange={e => {
                setLot(e.target.value); setReview(null); setReason(""); setTypedCode(""); setError(null);
              }}>
                <option value="">Kaynak lot seçin</option>
                {catalog.lots.map(l => <option value={l.id} key={l.id}>{l.external_code} · {catalog.products.find(p => p.id === l.product_id)?.name}{l.blocked ? " · Bloke" : ""}</option>)}
              </select>
            </label>
          </State>
          {!lot ? <Empty>Etki analizini başlatmak için bir kaynak lot seçin.</Empty> : <>
            <State loading={preview.isPending || preview.isFetching} error={preview.error}>
              {report && <>
                <p className="recall-context">Bu kapsam mevcut izleme görünümüdür; henüz kesinleşmiş recall sonucu değildir. Bu aşama kayıt veya stok değişikliği oluşturmaz.</p>
                <div className="recall-source"><span>Seçili kaynak</span><strong>{code}</strong><p>{report.source_lot.product.name}</p><Badge tone={report.source_lot.blocked ? "danger" : ""}>{report.source_lot.blocked ? "Zaten bloke" : "Bloke değil"}</Badge></div>
                {report.lots.some(l => l.blocked) && <div className="notice warning">Kapsamda zaten bloke lot var. Yeni bir kayıt blokları kaldırmaz; önce mevcut geri çağırma kayıtlarını inceleyin.</div>}
                <ImpactSummary report={report} />
                <h4>Etkilenen lotlar ve kayıtlı şirket stoğu</h4>
                <p className="caption">Kaynak ve gerçek üretim ilişkilerindeki türevler. Diğer bileşenler sırf aynı üretimde kullanıldı diye kaynak lotun türevi sayılmaz.</p>
                <div className="recall-card-grid">
                  {report.lots.map(l => <article className="recall-card" key={l.id}>
                    <div className="recall-card-head"><strong>{l.external_code}</strong><Badge tone={l.blocked ? "danger" : ""}>{l.id === lot ? "Kaynak" : "Türev"}{l.blocked ? " · Bloke" : ""}</Badge></div>
                    <p>{l.product.name}</p>
                    {report.stocks.filter(s => s.lot_id === l.id).map(s => <p className="recall-stock" key={s.location_id}><span>{s.location.name}</span><strong>{amount(s.quantity)} {units[s.unit]}</strong></p>)}
                    {!report.stocks.some(s => s.lot_id === l.id) && <p>Kayıtlı stok satırı yok.</p>}
                    <small>Kayıtlı miktar, satışa uygunluk garantisi değildir.</small>
                  </article>)}
                </div>
                <h4>Kayıtlı birinci ve ikinci kademe alıcılar</h4>
                <p className="recall-context">Dış market fiziksel stoğu ve tüketiciye satış: <strong>Bilinmiyor</strong>. İkinci kademe miktarları şirket sevkiyatına tekrar eklenmez.</p>
                {!report.buyers.length && <Empty>Bu kapsamda kayıtlı alıcı bulunmuyor.</Empty>}
                <div className="recall-card-grid">
                  {report.buyers.map(b => <article className="recall-card" key={b.customer_id}>
                    <h5>{b.current_customer.name}</h5><p>{b.current_customer.contact || "Güncel iletişim kaydedilmemiş"}</p>
                    {b.quantities.map(q => <p key={q.lot_id + q.unit}>{report.lots.find(l => l.id === q.lot_id)?.external_code} · Kayıtlı sevk: <strong>{amount(q.shipped_quantity)} {units[q.unit]}</strong></p>)}
                    <p>{b.recipient_snapshots.length} sevkiyat alıcı kaydı</p>
                    <DistributionEvidence report={report} customerId={b.customer_id} />
                  </article>)}
                </div>
              </>}
            </State>
            <div className="recall-actions">
              <button type="button" className="button" disabled={preview.isFetching} onClick={() => void preview.refetch()}>Etki analizini yenile</button>
              <button type="button" className="button" disabled={!ready} onClick={() => { setReview(preview.data!); setStep(2); }}>Gerekçe ve riske ilerle <ArrowRight size={16} /></button>
            </div>
          </>}
        </>}
        {step >= 2 && report && <>
          <div className="recall-source"><span>Yeniden kontrol edin · Seçili kaynak</span><strong>{code}</strong><p>{report.source_lot.product.name} · {report.source_lot.blocked ? "Zaten bloke" : "Bloke değil"}</p></div>
          <Risk />
          <ImpactSummary report={report} />
          <p>Kesinleştirme, gerçek lot ilişkilerine bağlı geri çağırma üyeliğini kaydeder ve etkilenen lotları atomik olarak bloke eder. Geçmiş satış/sevkiyat silinmez; stok miktarı ve maliyet defteri değiştirilmez.</p>
          <form onSubmit={e => { e.preventDefault(); if (validReason && ready) { setTypedCode(""); setStep(3); setShowConfirm(true); } }}>
            <label className="field" htmlFor="recall-reason">Geri çağırma nedeni <span>(zorunlu)</span>
              <textarea id="recall-reason" aria-label="Geri çağırma nedeni" value={reason} onChange={e => setReason(e.target.value)} maxLength={500} required rows={4} aria-describedby="recall-reason-help" />
            </label>
            <p id="recall-reason-help" className="caption">Gıda güvenliği riskini ve kaynağı açıklayın. En fazla 500 karakter.</p>
            <div className="recall-actions">
              <button type="button" className="button" onClick={() => { setReview(null); setStep(1); }}><ArrowLeft size={16} /> Kaynak ve etkiye dön</button>
              <button ref={reviewButton} type="submit" className="button" disabled={!validReason || !ready}>Geri çağırmayı gözden geçir <ArrowRight size={16} /></button>
            </div>
          </form>
        </>}
      </>}
      {showConfirm && report && <ConfirmDialog title="Son kontrol · Geri çağırma" danger confirmLabel={finalLabel}
        confirmDisabled={typedCode !== code || !validReason || busy || !ready}
        onCancel={() => { restoreFocus.current = true; setShowConfirm(false); setTypedCode(""); setStep(2); }} onConfirm={finalize}>
        <Risk />
        <p><strong>Kaynak: {code}</strong> · {report.source_lot.product.name}</p>
        <ImpactSummary report={report} compact />
        <p>Bloke edilecek lotlar: {report.lots.map(l => l.external_code).join(", ")}</p>
        <p>Konumlar: {[...new Set(report.stocks.map(s => s.location.name))].join(", ") || "Kayıt yok"}</p>
        <p>İlk kademe alıcılar: {report.buyers.map(b => b.current_customer.name).join(", ") || "Kayıt yok"}</p>
        <p>İkinci kademe alıcılar: {[...new Set(report.second_tier_distributions.map(r => r.recipient_name))].join(", ") || "Belgelenmemiş"}</p>
        <p>Gerekçe: {reason.trim()}</p>
        <label className="field" htmlFor="recall-confirm-code">Kaynak lot kodunu elle yazın
          <input id="recall-confirm-code" value={typedCode} onChange={e => setTypedCode(e.target.value)} autoComplete="off" spellCheck={false} maxLength={100} aria-describedby="recall-code-help" aria-invalid={!!typedCode && typedCode !== code} />
        </label>
        <p id="recall-code-help">Tam olarak <strong>{code}</strong> yazın. {typedCode && typedCode !== code ? "Lot kodu eşleşmiyor." : ""}</p>
      </ConfirmDialog>}
    </div>
  </Section>;
}
