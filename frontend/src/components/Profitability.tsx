import { useQuery } from "@tanstack/react-query";
import { request } from "../lib/api";
import type { Profitability, ProfitMetrics } from "../lib/operational-types";
import { Badge, Section, State, Table } from "./ui";
import { CriticalNotice, LotLink, RecordId, StatCard } from "./workflow";
import { amount, eur, units } from "../lib/format";
import { displayDecimal } from "../lib/presentation";
const states = {
  active: "Aktif",
  cancelled: "İptal edildi",
  returned: "Tam iade",
  partially_returned: "Kısmi iade",
};
export function ProfitMetricsView({ metrics }: { metrics: ProfitMetrics }) {
  return (
    <div className="stat-grid">
      <StatCard
        label="Kayıtlı net satış geliri"
        value={eur(metrics.net_revenue_eur)}
      />
      <StatCard
        label="Kayıtlı tüketim maliyeti"
        value={eur(metrics.recognized_cost_eur)}
      />
      <StatCard
        label="Brüt kâr"
        value={eur(metrics.gross_profit_display_eur)}
      />
      <StatCard
        label="Brüt kâr marjı"
        value={
          metrics.margin_percent == null
            ? "Hesaplanamıyor"
            : displayDecimal(metrics.margin_percent, 2) + " %"
        }
      />
    </div>
  );
}
export function ProfitabilityPanel({ saleId }: { saleId: string }) {
  const query = useQuery({
    queryKey: ["profitability", saleId],
    queryFn: () =>
      request<Profitability>("/sales/" + saleId + "/profitability"),
    retry: false,
  });
  return (
    <Section
      title="Satış kârlılığı"
      subtitle="Gelir, maliyet, kâr ve marj kesin backend kayıtlarından alınır."
    >
      <State loading={query.isPending} error={query.error}>
        {query.data && (
          <div className="stack">
            <Badge
              tone={
                query.data.adjustments.state === "active" ? "green" : "amber"
              }
            >
              {states[query.data.adjustments.state]}
            </Badge>
            <ProfitMetricsView metrics={query.data} />
            <Table
              headers={[
                "Lot",
                "Miktar",
                "VKP / birim satış fiyatı",
                "Kayıtlı birim maliyet",
              ]}
              empty={!query.data.lines.length}
            >
              {query.data.lines.map((line) => (
                <tr key={line.sale_line_id}>
                  <td>
                    <LotLink id={line.lot_id} />
                  </td>
                  <td>
                    {amount(line.quantity)} {units[line.unit]}
                  </td>
                  <td>{eur(line.vkp_eur_per_unit)}</td>
                  <td>{eur(line.recognized_unit_cost_eur)}</td>
                </tr>
              ))}
            </Table>
            {query.data.adjustments.state !== "active" && (
              <div className="stack correction-summary">
                <h3>İade / iptal sonrası netleşmiş sonuç</h3>
                <ProfitMetricsView metrics={query.data.net_after_adjustments} />
                <p>
                  Kayıtlı iade gelir düzeltmesi:{" "}
                  {eur(query.data.adjustments.return_credit_eur)} · İptal gelir
                  düzeltmesi:{" "}
                  {eur(query.data.adjustments.cancellation_credit_eur)} ·
                  Tarihsel maliyet düzeltmesi:{" "}
                  {eur(query.data.adjustments.cost_reversal_eur)}
                </p>
                <CriticalNotice>
                  Nakit geri ödeme kaydı yok. Orijinal satış ve tüketim geçmişi
                  korunur; iadeler karantinadadır.
                </CriticalNotice>
                {query.data.adjustments.return_ids.map((id) => (
                  <RecordId key={id} id={id} label="İade kaydı" />
                ))}
                {query.data.adjustments.cancellation_id && (
                  <RecordId
                    id={query.data.adjustments.cancellation_id}
                    label="İptal kaydı"
                  />
                )}
              </div>
            )}
            <details>
              <summary>Hesabın sınırları ve kesin değerler</summary>
              <ul>
                {query.data.limitations.map((text) => (
                  <li key={text}>{text}</li>
                ))}
              </ul>
              <p>
                Ham kayıtlı maliyet: {query.data.recognized_cost_eur} EUR · Ham
                brüt kâr: {query.data.gross_profit_eur} EUR · Ham marj:{" "}
                {query.data.margin_percent ?? "null"} %.
              </p>
              <p>
                Vergi, indirim ve genel gider bu ekranda hesaplanmaz.
                Gösterimden yeniden maliyet türetilmez.
              </p>
            </details>
          </div>
        )}
      </State>
    </Section>
  );
}
