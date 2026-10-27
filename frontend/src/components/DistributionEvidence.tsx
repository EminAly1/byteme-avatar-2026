import { Link } from "react-router-dom";
import type { TraceReport } from "../lib/modules";
import { amount, dateTime, units } from "../lib/format";
import { LotLink } from "./workflow";
export function DistributionEvidence({
  report,
  customerId,
}: {
  report: TraceReport;
  customerId: string;
}) {
  const records = report.second_tier_distributions.filter(
    (row) => row.source_customer_id === customerId,
  );
  const unknown = report.unknown_distributions.find(
    (row) => row.customer_id === customerId,
  );
  return (
    <div className="distribution-evidence">
      <h4>İkinci kademe alıcılar</h4>
      {!records.length ? (
        <p>
          İkinci kademe alıcı: <strong>Bilinmiyor</strong>
        </p>
      ) : (
        <>
          {records.map((row) => (
            <article className="evidence-record" key={row.id}>
              <strong>{row.recipient_name}</strong>
              <p>
                {amount(row.quantity)} {units[row.unit]} · {row.reference}
              </p>
              <p className="caption">
                {dateTime(row.distributed_at)} ·{" "}
                {row.recipient_contact || "İletişim kaydedilmemiş"}
              </p>
              <Link className="text-button" to={"/dagitimlar/" + row.id}>
                Kayıtlı bildirimi aç
              </Link>
            </article>
          ))}
          <p className="caption">
            Kısmi operatör bildirimi; diğer dağıtımların tamamının bilindiği
            veya marketçe bağımsız doğrulandığı anlamına gelmez.
          </p>
        </>
      )}
      {unknown?.unallocated_documented_quantities?.map((row) => (
        <div className="documented-remainder" key={row.source_shipment_line_id}>
          <p>
            Belgelenmiş tahsis edilmemiş miktar — fiziksel stok doğrulanmadı
          </p>
          <strong>
            {amount(row.quantity)} {units[row.unit]}
          </strong>{" "}
          <LotLink
            id={row.lot_id}
            code={
              report.lots.find((lot) => lot.id === row.lot_id)?.external_code
            }
          />
        </div>
      ))}
    </div>
  );
}
