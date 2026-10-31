import { useState } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useFormContext } from "react-hook-form";
import { Network } from "lucide-react";
import { CommandForm, Field, Options } from "../components/forms";
import { Badge, Section, State, Table } from "../components/ui";
import {
  CriticalNotice,
  LotLink,
  ModuleIntro,
  RecordId,
  ReviewSummary,
} from "../components/workflow";
import { useCatalog, useRecords, useRecordDetails } from "../lib/data";
import { request } from "../lib/api";
import { amount, dateTime, decimal, units } from "../lib/format";
import { distributionSchema, turkeyNow } from "../lib/operational-validation";
import type { SecondTier } from "../lib/operational-types";
import type { Shipment, ShipmentDetail, ShipmentLine } from "../lib/modules";

type Source = { shipment: ShipmentDetail; line: ShipmentLine };
type Catalog = ReturnType<typeof useCatalog>;
function DistributionFields({
  sources,
  data,
}: {
  sources: Source[];
  data: Catalog;
}) {
  const { watch } = useFormContext();
  const source = sources.find(
    (row) => row.line.id === watch("source_shipment_line_id"),
  );
  return (
    <>
      <div className="form-grid">
        <Field name="source_shipment_line_id" label="Kaynak sevkiyat satırı">
          <option value="">Market / lot / sevkiyat seçin</option>
          {sources.map(({ shipment, line }) => (
            <option value={line.id} key={line.id}>
              {shipment.recipient_name} ·{" "}
              {data.lots.find((lot) => lot.id === line.lot_id)?.external_code} ·{" "}
              {amount(line.quantity)} {units[line.unit]}
            </option>
          ))}
        </Field>
        <Field name="recipient_party_id" label="İkinci kademe alıcı">
          <Options
            items={data.parties.filter(
              (party) => party.id !== source?.shipment.customer_id,
            )}
          />
        </Field>
        <Field
          name="quantity"
          label="Bildirilen miktar"
          type="decimal"
          hint={
            source
              ? units[source.line.unit] + "; miktarı backend denetler."
              : "Kaynak sevkiyatın birimi kullanılır."
          }
        />
        <Field
          name="distributed_at"
          label="Dağıtım tarihi ve saati"
          type="datetime-local"
          hint="Türkiye saati (UTC+03:00)."
        />
        <Field name="reference" label="Dağıtım referansı" />
        <Field name="evidence_note" label="Bildirim açıklaması" />
      </div>
      {source && (
        <p className="caption">
          Şirketin kayıtlı kaynak sevkiyatı: {amount(source.line.quantity)}{" "}
          {units[source.line.unit]}. Bu miktar marketin mevcut stoğu değildir.
        </p>
      )}
    </>
  );
}
export function DistributionDetail({ record }: { record: SecondTier }) {
  return (
    <Section title="Kayıtlı ikinci kademe bildirimi">
      <div className="stack">
        <Badge>Operatör bildirimi · bağımsız market teyidi yok</Badge>
        <ReviewSummary
          items={[
            ["Kaynak market", record.source_recipient_snapshot.name],
            ["Kayıtlı alıcı", record.recipient_name],
            ["Miktar", `${amount(record.quantity)} ${units[record.unit]}`],
            ["Bildirim tarihi", dateTime(record.distributed_at)],
            ["Referans", record.reference],
            [
              "Kayıt anındaki iletişim",
              record.recipient_contact || "Kaydedilmemiş",
            ],
          ]}
        />
        <p>{record.evidence_note}</p>
        <CriticalNotice>
          Şirket stoğu ve geliri bu bildirimle değişmez. Marketin ve alıcının
          fiziksel stoğu, son tüketici satışları bilinmiyor.
        </CriticalNotice>
        <div className="quick-links">
          <Link
            className="button"
            to={"/sevkiyatlar?shipment=" + record.source_shipment_id}
          >
            Kaynak sevkiyat
          </Link>
          <LotLink id={record.source_lot_id} />
        </div>
        <RecordId id={record.id} label="Dağıtım kaydı" />
        <RecordId
          id={record.source_shipment_line_id}
          label="Kaynak sevkiyat satırı"
        />
        <RecordId id={record.recipient_party_id} label="Alıcı kaydı" />
      </div>
    </Section>
  );
}
export function Distributions() {
  const data = useCatalog(),
    headers = useRecords<Shipment>("/shipments");
  const shipments = useRecordDetails<ShipmentDetail>(
    "/shipments",
    headers.data?.map((row) => row.id),
  );
  const records = useRecords<SecondTier>("/distributions/second-tier");
  const { id = "" } = useParams();
  const [search] = useSearchParams(),
    navigate = useNavigate();
  const [sourceFilter, setSourceFilter] = useState("");
  const detail = useQuery({
    queryKey: ["second-tier", id],
    queryFn: () => request<SecondTier>("/distributions/second-tier/" + id),
    enabled: !!id,
    retry: false,
  });
  const sources = (shipments.data || []).flatMap((shipment) =>
    shipment.lines.map((line) => ({ shipment, line })),
  );
  return (
    <State
      loading={
        data.loading ||
        headers.isPending ||
        shipments.isPending ||
        records.isPending
      }
      error={data.error || headers.error || shipments.error || records.error}
    >
      <div className="stack">
        <ModuleIntro
          icon={<Network size={24} />}
          title="Kayıtlı dağıtım, açık sınırlar."
          description="Şirket sevkiyatından sonraki bildirimi gerçek alıcı ve lot kaydına bağlayın. Dış stok veya yeni şirket satışı oluşturulmaz."
        />
        {id && (
          <State loading={detail.isPending} error={detail.error}>
            {detail.data && (
              <>
                <Link className="text-button" to="/dagitimlar">
                  ← Dağıtım listesi
                </Link>
                <DistributionDetail record={detail.data} />
              </>
            )}
          </State>
        )}
        <Section title="İkinci kademe dağıtım listesi">
          <label className="field">
            Kaynak market filtresi
            <select
              value={sourceFilter}
              onChange={(event) => setSourceFilter(event.target.value)}
            >
              <option value="">Tüm kaynak marketler</option>
              {data.parties.map((party) => (
                <option key={party.id} value={party.id}>
                  {party.name}
                </option>
              ))}
            </select>
          </label>
          <Table readonlyReason="Kesin kayıt korunur. Düzeltme yalnız desteklenen iade, iptal veya yeni işlemle yapılır."
            headers={[
              "Referans / kaynak",
              "Kayıtlı alıcı",
              "Miktar",
              "Tarih",
              "Ayrıntı",
            ]}
            empty={
              !records.data?.filter(
                (row) =>
                  !sourceFilter || row.source_customer_id === sourceFilter,
              ).length
            }
          >
            {records.data
              ?.filter(
                (row) =>
                  !sourceFilter || row.source_customer_id === sourceFilter,
              )
              .map((row) => (
                <tr key={row.id}>
                  <td>
                    <strong>{row.reference}</strong>
                    <small>{row.source_recipient_snapshot.name}</small>
                  </td>
                  <td>{row.recipient_name}</td>
                  <td>
                    {amount(row.quantity)} {units[row.unit]}
                  </td>
                  <td>{dateTime(row.distributed_at)}</td>
                  <td>
                    <Link className="text-button" to={"/dagitimlar/" + row.id}>
                      Bildirimi aç
                    </Link>
                  </td>
                </tr>
              ))}
          </Table>
        </Section>
        <Section title="İkinci kademe bildirimi oluştur">
          <CriticalNotice>
            Bu kayıt sistem operatörünün bildirimidir. Marketin bağımsız
            doğrulaması, fiziksel stok veya tüketici satışı kanıtlanmış
            sayılmaz.
          </CriticalNotice>
          <CommandForm
            schema={distributionSchema}
            defaults={{
              source_shipment_line_id: search.get("source") || "",
              recipient_party_id: "",
              quantity: "",
              distributed_at: turkeyNow(),
              reference: "",
              evidence_note: "",
            }}
            path="/distributions/second-tier"
            label="Bildirimi gözden geçir"
            confirmText="Kayıtlı kaynak sevkiyata ikinci kademe bildirimi eklenecek. Şirketten ikinci stok çıkışı veya gelir oluşmaz."
            payload={(value) => ({
              ...value,
              quantity: decimal(value.quantity),
              unit: sources.find(
                (row) => row.line.id === value.source_shipment_line_id,
              )!.line.unit,
              distributed_at: new Date(
                value.distributed_at + "+03:00",
              ).toISOString(),
            })}
            summary={(body) => {
              const value = body as {
                source_shipment_line_id: string;
                recipient_party_id: string;
                quantity: string;
                unit: keyof typeof units;
                distributed_at: string;
                reference: string;
              };
              return (
                <ReviewSummary
                  items={[
                    [
                      "Kaynak market",
                      sources.find(
                        (row) => row.line.id === value.source_shipment_line_id,
                      )?.shipment.recipient_name,
                    ],
                    [
                      "Alıcı",
                      data.parties.find(
                        (row) => row.id === value.recipient_party_id,
                      )?.name,
                    ],
                    [
                      "Miktar",
                      `${amount(value.quantity)} ${units[value.unit]}`,
                    ],
                    ["Tarih", dateTime(value.distributed_at)],
                    ["Referans", value.reference],
                  ]}
                />
              );
            }}
            onSuccess={(result) =>
              navigate("/dagitimlar/" + (result as SecondTier).id)
            }
          >
            <DistributionFields sources={sources} data={data} />
          </CommandForm>
        </Section>
      </div>
    </State>
  );
}
