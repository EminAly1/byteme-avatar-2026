import { DistributionEvidence } from "../components/DistributionEvidence";
import { useState } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Network,
  ShieldAlert,
  ArrowDown,
  Package,
  Factory,
  Building2,
} from "lucide-react";
import { RecallWizard } from "../components/RecallWizard";
import { Badge, Section, State, Table, Empty } from "../components/ui";
import {
  CriticalNotice,
  DetailDrawer,
  FilterBar,
  LotLink,
  ModuleIntro,
  RecordId,
  ReviewSummary,
  StatCard,
} from "../components/workflow";
import { useCatalog } from "../lib/data";
import { request } from "../lib/api";
import { amount, dateTime, units } from "../lib/format";
import type { Recall, TraceLot, TraceReport } from "../lib/modules";
import { readHistory, remember } from "../lib/history";

export function BuyerReport({ report }: { report: TraceReport }) {
  return (
    <Section
      title="Bilinen marketler ve sevkiyatlar"
      subtitle="Kayıtlı ilk kademe teslimatlar. Satışa bağlı sevkiyat ikinci kez toplanmaz."
    >
      <div className="shipment-totals">
        {report.total_shipped_quantities.map((t) => (
          <div key={t.product_id + t.unit}>
            <span>
              {report.lots.find((l) => l.product_id === t.product_id)?.product
                .name || "Kayıtlı ürün"}{" "}
              · Toplam sevk
            </span>
            <strong>
              {amount(t.quantity)} {units[t.unit]}
            </strong>
          </div>
        ))}
      </div>
      {!report.buyers.length ? (
        <Empty>Bu kapsamda kayıtlı alıcı bulunmuyor.</Empty>
      ) : (
        <div className="buyer-grid">
          {[...report.buyers]
            .sort((a, b) =>
              a.current_customer.name.localeCompare(
                b.current_customer.name,
                "tr",
              ),
            )
            .map((b) => (
              <article className="buyer-card" key={b.customer_id}>
                <div className="buyer-heading">
                  <Building2 size={20} />
                  <h3>{b.current_customer.name}</h3>
                </div>
                {b.quantities.map((q) => (
                  <div className="buyer-quantity" key={q.lot_id + q.unit}>
                    <LotLink
                      id={q.lot_id}
                      code={
                        report.lots.find((l) => l.id === q.lot_id)
                          ?.external_code
                      }
                    />
                    <dl>
                      <div>
                        <dt>Sevk edilmiş</dt>
                        <dd>
                          {amount(q.shipped_quantity)} {units[q.unit]}
                        </dd>
                      </div>
                      <div>
                        <dt>Kayıtlı satış</dt>
                        <dd>
                          {amount(q.recorded_sale_quantity)} {units[q.unit]}
                        </dd>
                      </div>
                    </dl>
                  </div>
                ))}
                <p className="unknown-note">
                  Market kalanı: <strong>Bilinmiyor</strong>
                  <br />
                  Son tüketici satışı: <strong>Bilinmiyor</strong>
                </p>
                <DistributionEvidence
                  report={report}
                  customerId={b.customer_id}
                />
                <details>
                  <summary>Alıcı iletişimi ve teslim belgeleri</summary>
                  {b.recipient_snapshots.map((r, i) => (
                    <div
                      className="contact-snapshot"
                      key={r.shipment_id + "-" + i}
                    >
                      <strong>{r.recipient_name}</strong>
                      <p>
                        {r.recipient_contact ||
                          "İletişim bilgisi kaydedilmemiş"}
                      </p>
                      <Link
                        className="text-button"
                        to={"/sevkiyatlar?shipment=" + r.shipment_id}
                      >
                        Teslim belgesi · {dateTime(r.shipped_at)}
                      </Link>
                    </div>
                  ))}
                  <RecordId id={b.customer_id} label="Müşteri referansı" />
                </details>
              </article>
            ))}
        </div>
      )}
    </Section>
  );
}
function LotCard({ lot, onOpen }: { lot: TraceLot; onOpen: () => void }) {
  return (
    <button className="trace-lot" onClick={onOpen}>
      <Package size={19} />
      <span>
        <strong>{lot.external_code}</strong>
        <small>
          {lot.product.name} · {amount(lot.original_quantity)}{" "}
          {units[lot.product.base_unit]}
        </small>
        <small>Lot ayrıntısını aç →</small>
      </span>
      <Badge tone={lot.blocked ? "red" : "green"}>
        {lot.blocked ? "Bloke" : "Bloke değil"}
      </Badge>
    </button>
  );
}
export function TraceReportView({
  report,
  showBuyers = true,
}: {
  report: TraceReport;
  showBuyers?: boolean;
}) {
  const [selected, setSelected] = useState<TraceLot | null>(null);
  const lotById = (id: string) =>
    [...report.lots, ...report.context_lots].find((l) => l.id === id);
  return (
    <div className="stack">
      {report.cycle_detected && (
        <CriticalNotice>
          Kayıt grafında döngü bulundu. Kesin ilişkiler gösteriliyor; kayıtları
          inceleyin.
        </CriticalNotice>
      )}
      <Section
        title={
          report.direction === "backward"
            ? "Kaynaklara doğru kayıt zinciri"
            : "Kaynak lotun ileri kayıt zinciri"
        }
        subtitle="Bağlantılar gerçek operasyon ve FK kayıtlarıdır. Miktar atfı fiziksel ayrıştırma kanıtı değildir."
      >
        <ol className="trace-flow">
          <li>
            <span className="flow-node">
              <Package size={18} />
            </span>
            <div>
              <p className="eyebrow">SEÇİLEN LOT</p>
              <LotCard
                lot={report.source_lot}
                onOpen={() => setSelected(report.source_lot)}
              />
            </div>
          </li>
          {report.operations.map((op) => (
            <li key={op.id}>
              <span className="flow-node">
                <Factory size={18} />
              </span>
              <div className="flow-operation">
                <div className="section-head">
                  <div>
                    <p className="eyebrow">KAYITLI İŞLEM</p>
                    <h3>{op.code}</h3>
                  </div>
                  <Link
                    className="text-button"
                    to={
                      (op.kind === "cutting"
                        ? "/parcalama/"
                        : op.kind === "rework"
                          ? "/hareketler/rework/"
                          : "/uretim/") + op.id
                    }
                  >
                    İşlemi aç
                  </Link>
                </div>
                <div className="edge-list">
                  {report.edges
                    .filter((e) => e.operation_id === op.id)
                    .map((e) => (
                      <div
                        className="trace-edge"
                        key={e.input_id + e.output_id}
                      >
                        <div>
                          <strong>
                            {lotById(e.input_lot_id)?.external_code ||
                              e.input_lot_id}
                          </strong>
                          <small>
                            Tüketim: {amount(e.consumed_input_quantity)}{" "}
                            {
                              units[
                                lotById(e.input_lot_id)?.product.base_unit ||
                                  "kg"
                              ]
                            }
                          </small>
                        </div>
                        <ArrowDown size={18} />
                        <div>
                          <strong>
                            {lotById(e.output_lot_id)?.external_code ||
                              e.output_lot_id}
                          </strong>
                          <small>
                            Çıktı: {amount(e.output_quantity)}{" "}
                            {
                              units[
                                lotById(e.output_lot_id)?.product.base_unit ||
                                  "kg"
                              ]
                            }
                          </small>
                        </div>
                        <details>
                          <summary>Bağlantı referansı ve atıf</summary>
                          <p className="caption">
                            Bağlantı kaydı:{" "}
                            <span className="code">
                              {e.lot_link_id || "Miktar atfı kaydedilmemiş"}
                            </span>
                            {e.attributed_input_quantity !== null &&
                              " · Atfedilen giriş: " +
                                amount(e.attributed_input_quantity)}
                          </p>
                        </details>
                      </div>
                    ))}
                </div>
                {!report.edges.some((e) => e.operation_id === op.id) && (
                  <p className="caption">
                    İşlem henüz kapanmamış; türev lot kaydı yok.
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
        <p className="caption">
          Ortak girdinin toplam tüketimi her bağlantıda bilgi olarak tekrar
          görünür; kenarlar toplanarak tüketim hesaplanmaz.
        </p>
      </Section>
      <Section
        title="Kapsamdaki lotlar"
        subtitle={
          report.direction === "forward"
            ? "Seçilen kaynak ve kesin kayıtlardan ulaşılan türevler"
            : "Seçilen mamul/parça ve kayıtlı ataları"
        }
      >
        <div className="lot-card-grid">
          {report.lots.map((l) => (
            <LotCard key={l.id} lot={l} onOpen={() => setSelected(l)} />
          ))}
        </div>
        <details className="context-details">
          <summary>
            İşlem bağlamındaki diğer lotlar ({report.context_lots.length})
          </summary>
          <p className="caption">
            Bu liste tek başına geri çağırma üyeliği veya kaynak lot ilişkisi oluşturmaz.
          </p>
          {report.context_lots.map((l) => (
            <LotCard key={l.id} lot={l} onOpen={() => setSelected(l)} />
          ))}
        </details>
      </Section>
      <Section title="Kayıtlı konum bakiyeleri">
        <Table
          headers={["Lot", "Konum", "Bakiye", "Kullanılabilir", "Durum"]}
          empty={!report.stocks.length}
        >
          {report.stocks.map((s) => (
            <tr key={s.lot_id + s.location_id}>
              <td>
                <LotLink
                  id={s.lot_id}
                  code={lotById(s.lot_id)?.external_code}
                />
              </td>
              <td>{s.location.name}</td>
              <td>
                {amount(s.quantity)} {units[s.unit]}
              </td>
              <td>
                {amount(s.available_quantity)} {units[s.unit]}
              </td>
              <td>
                <Badge tone={s.blocked ? "red" : ""}>
                  {s.blocked ? "Bloke" : "Sunucu kaydı"}
                </Badge>
              </td>
            </tr>
          ))}
        </Table>
      </Section>
      {showBuyers && <BuyerReport report={report} />}
      {selected && (
        <DetailDrawer title="Lot ayrıntısı" onClose={() => setSelected(null)}>
          <div className="stack">
            <h3>{selected.external_code}</h3>
            <RecordId id={selected.id} label="Lot UUID" />
            <ReviewSummary
              items={[
                ["Ürün", selected.product.name],
                ["Tedarikçi", selected.supplier?.name || "Kaydedilmemiş"],
                [
                  "Alış/üretim miktarı",
                  amount(selected.original_quantity) +
                    " " +
                    units[selected.product.base_unit],
                ],
                ["Giriş zamanı", dateTime(selected.received_at)],
                ["Son tüketim tarihi", selected.expires_at || "Kaydedilmemiş"],
                ["Bloke", selected.blocked ? "Evet" : "Hayır"],
              ]}
            />
            <Link
              className="button"
              onClick={() => setSelected(null)}
              to={"/izlenebilirlik?lot=" + selected.id}
            >
              Bu lotu izle
            </Link>
          </div>
        </DetailDrawer>
      )}
    </div>
  );
}
export function Traceability() {
  const data = useCatalog(),
    [params, setParams] = useSearchParams();
  const lot = params.get("lot") || "",
    direction = params.get("direction") === "backward" ? "backward" : "forward";
  const q = useQuery({
    queryKey: ["trace", lot, direction],
    queryFn: () =>
      request<TraceReport>(`/lots/${lot}/trace?direction=${direction}`),
    enabled: !!lot,
    retry: false,
  });
  return (
    <div className="stack">
      <ModuleIntro
        title="Her lotun kaynağı ve yolu belli."
        description="Hammaddeden bilinen alıcıya, mamulden kaynağa: yalnız kayıtlı ilişkileri izleyin."
        icon={<Network size={24} />}
      />
      <Section title="Lot seçimi">
        <State loading={data.loading} error={data.error}>
          <FilterBar>
            <label>
              İzlenecek lot
              <select
                aria-label="İzlenecek lot"
                value={lot}
                onChange={(e) => setParams({ lot: e.target.value, direction })}
              >
                <option value="">Lot seçin</option>
                {data.lots.map((l) => (
                  <option value={l.id} key={l.id}>
                    {l.external_code} ·{" "}
                    {data.products.find((p) => p.id === l.product_id)?.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              İzleme yönü
              <select
                aria-label="İzleme yönü"
                value={direction}
                onChange={(e) => setParams({ lot, direction: e.target.value })}
              >
                <option value="forward">İleri · kaynak → alıcılar</option>
                <option value="backward">Geri · mamul → kaynaklar</option>
              </select>
            </label>
          </FilterBar>
        </State>
      </Section>
      {lot ? (
        <State loading={q.isPending} error={q.error}>
          {q.data && <TraceReportView key={lot + direction} report={q.data} />}
        </State>
      ) : (
        <Empty>Bir lot seçerek kayıt zincirini açın.</Empty>
      )}
    </div>
  );
}
export function Recalls() {
  const navigate = useNavigate();
  const [lookup, setLookup] = useState(""),
    [lookupError, setLookupError] = useState("");
  return (
    <div className="stack">
      <ModuleIntro
        title="Risk kapsamını görün, kontrollü ilerleyin."
        description="Kaynak lotun kayıtlı etkisini inceleyin. Geri çağırma ancak açık onayınızla kesinleşir."
        icon={<ShieldAlert size={24} />}
      />
      <RecallWizard onSuccess={(record) => {
        remember("recalls", { id: record.id, at: record.created_at, label: record.reason });
        navigate("/geri-cagirma/" + record.id);
      }} />
      <Section
        title="Kayıtlı geri çağırmayı aç"
        subtitle="Elinizdeki kayıt kimliğiyle sonuca ulaşın. Aşağıda bu tarayıcı sekmesinde oluşturulan kayıtlar bulunur."
      >
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (!/^[0-9a-f-]{36}$/i.test(lookup)) {
              setLookupError("Geçerli bir geri çağırma kayıt kimliği girin.");
              return;
            }
            navigate("/geri-cagirma/" + lookup);
          }}
        >
          <div className="field">
            <label htmlFor="recall-lookup">Geri çağırma kayıt kimliği</label>
            <input id="recall-lookup" value={lookup} onChange={(e) => { setLookup(e.target.value); setLookupError(""); }}
              placeholder="Örn: 00000000-0000-4000-8000-000000000001" autoComplete="off"
              aria-invalid={!!lookupError} aria-describedby={lookupError ? "recall-lookup-help recall-lookup-error" : "recall-lookup-help"} />
            <small id="recall-lookup-help">Kayıt ayrıntılarındaki tam kimliği kopyalayın.</small>
          </div>
          <button className="button">Kaydı aç</button>
        </form>
        {lookupError && (
          <p id="recall-lookup-error" role="alert" className="field-error">
            {lookupError}
          </p>
        )}
        <div className="record-list">
          {readHistory("recalls").map((r) => (
            <Link
              className="record-card"
              key={r.id}
              to={"/geri-cagirma/" + r.id}
            >
              <div>
                <strong>{r.label}</strong>
                <p>{dateTime(r.at)}</p>
                <code>{r.id}</code>
              </div>
            </Link>
          ))}
        </div>
      </Section>
    </div>
  );
}
export function RecallPage() {
  const { id = "" } = useParams();
  const q = useQuery({
    queryKey: ["recall", id],
    queryFn: () => request<Recall>("/recalls/" + id),
    retry: false,
  });
  return (
    <State loading={q.isPending} error={q.error}>
      {q.data && (
        <div className="stack">
          <Link className="text-button" to="/geri-cagirma">
            ← Geri çağırma
          </Link>
          <div className="recall-banner">
            <ShieldAlert size={25} />
            <div>
              <Badge tone="red">GERİ ÇAĞIRMA AKTİF</Badge>
              <h2>{q.data.reason}</h2>
              <p>
                {dateTime(q.data.created_at)} · Kaynak:{" "}
                {q.data.report.source_lot.external_code}
              </p>
            </div>
          </div>
          <RecordId id={id} label="Geri çağırma kaydı" />
          <div className="stat-grid">
            <StatCard
              label="Bloke edilen lot"
              value={q.data.report.lots.length}
            />
            <StatCard
              label="Etkilenen mamul/parça lotu"
              value={q.data.report.affected_finished_lot_ids.length}
            />
            <StatCard
              label="Birinci kademe alıcı"
              value={q.data.report.buyers.length}
            />
            <StatCard
              label="Bloke pozitif bakiye"
              value={q.data.report.blocked_stocks.length}
            />
          </div>
          <BuyerReport report={q.data.report} />
          <TraceReportView report={q.data.report} showBuyers={false} />
        </div>
      )}
    </State>
  );
}
