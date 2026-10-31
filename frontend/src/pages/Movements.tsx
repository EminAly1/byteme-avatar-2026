import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useIsMutating, useQuery } from "@tanstack/react-query";
import { useFormContext } from "react-hook-form";
import { ArrowLeftRight } from "lucide-react";
import { CommandForm, Field, Options, ArrayError } from "../components/forms";
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
import { loadPending } from "../lib/pending";
import {
  amount,
  dateTime,
  decimal,
  eur,
  positive,
  short,
  units,
} from "../lib/format";
import {
  transferSchema,
  returnSchema,
  cancelSchema,
} from "../lib/operational-validation";
import type {
  Transfer,
  Correction,
  Profitability,
} from "../lib/operational-types";
import type {
  Sale,
  SaleDetail,
  Shipment,
  ShipmentDetail,
} from "../lib/modules";
import type { Stock } from "../lib/types";
import { Reworks } from "./Reworks";

type Catalog = ReturnType<typeof useCatalog>;
function StockRows({ stocks, data }: { stocks: Stock[]; data: Catalog }) {
  return (
    <Table readonlyReason="Kesin kayıt korunur. Düzeltme yalnız desteklenen iade, iptal veya yeni işlemle yapılır."
      headers={["Lot / konum", "Kayıtlı stok", "Kullanılabilir", "Durum"]}
      empty={!stocks.length}
    >
      {stocks.map((row) => (
        <tr key={row.lot_id + row.location_id}>
          <td>
            <LotLink
              id={row.lot_id}
              code={
                data.lots.find((lot) => lot.id === row.lot_id)?.external_code
              }
            />
            <small>
              {
                data.locations.find(
                  (location) => location.id === row.location_id,
                )?.name
              }
            </small>
          </td>
          <td>
            {amount(row.quantity)}{" "}
            {
              units[
                data.products.find((product) => product.id === row.product_id)
                  ?.base_unit || "kg"
              ]
            }
          </td>
          <td>{amount(row.available_quantity)}</td>
          <td>
            {data.locations.find((location) => location.id === row.location_id)
              ?.kind === "quarantine" ? (
              <Badge tone="amber">Karantina · satılabilir değil</Badge>
            ) : row.blocked ? (
              <Badge tone="red">Bloke</Badge>
            ) : (
              "Backend bakiyesi"
            )}
          </td>
        </tr>
      ))}
    </Table>
  );
}
function TransferFields({ data, stocks }: { data: Catalog; stocks: Stock[] }) {
  const { watch } = useFormContext();
  const [lotId, sourceId] = String(watch("source") || "").split("|");
  return (
    <>
      <div className="form-grid">
        <Field name="source" label="Kaynak lot / depo">
          <option value="">Lot ve depo seçin</option>
          {stocks
            .filter(
              (row) =>
                positive(row.quantity) &&
                data.locations.find(
                  (location) => location.id === row.location_id,
                )?.kind !== "external_producer",
            )
            .map((row) => (
              <option
                key={row.lot_id + row.location_id}
                value={row.lot_id + "|" + row.location_id}
              >
                {data.lots.find((lot) => lot.id === row.lot_id)?.external_code}{" "}
                ·{" "}
                {
                  data.locations.find(
                    (location) => location.id === row.location_id,
                  )?.name
                }{" "}
                · {amount(row.quantity)}{" "}
                {
                  units[
                    data.products.find(
                      (product) => product.id === row.product_id,
                    )?.base_unit || "kg"
                  ]
                }
              </option>
            ))}
        </Field>
        <Field name="to_location_id" label="Hedef depo">
          <Options
            items={data.locations.filter(
              (location) =>
                location.kind !== "external_producer" &&
                location.id !== sourceId,
            )}
          />
        </Field>
        <Field name="quantity" label="Transfer miktarı" type="decimal" />
        <Field name="reference" label="Transfer referansı" />
        <Field name="reason" label="Transfer nedeni" />
      </div>
      {lotId && (
        <>
          <p className="caption">
            İşlem öncesi kayıtlı bakiye. Son bakiye onaydan sonra backend'den
            yenilenir.
          </p>
          <StockRows
            data={data}
            stocks={stocks.filter(
              (row) =>
                row.lot_id === lotId &&
                [sourceId, watch("to_location_id")].includes(row.location_id),
            )}
          />
        </>
      )}
    </>
  );
}
function Transfers({ data, stocks }: { data: Catalog; stocks: Stock[] }) {
  const records = useRecords<Transfer>("/transfers");
  const [created, setCreated] = useState<Transfer | null>(null);
  return (
    <div className="stack">
      <Section title="Depo transferi">
        <CriticalNotice>
          Karantinadan çıkış kalite onayı gerektirir. Blokaj, birim ve yeterli
          stok denetimini backend yapar.
        </CriticalNotice>
        <CommandForm
          schema={transferSchema}
          defaults={{
            source: "",
            to_location_id: "",
            quantity: "",
            reference: "",
            reason: "",
          }}
          path="/transfers"
          label="Transferi gözden geçir"
          confirmText="Aynı lot seçili depodan hedefe taşınacak. Maliyet yeniden tüketilmez."
          payload={(value) => {
            const [lot_id, from_location_id] = value.source.split("|");
            return {
              lot_id,
              from_location_id,
              to_location_id: value.to_location_id,
              quantity: decimal(value.quantity),
              unit: data.products.find(
                (product) =>
                  product.id ===
                  data.lots.find((lot) => lot.id === lot_id)?.product_id,
              )!.base_unit,
              reference: value.reference || null,
              reason: value.reason,
            };
          }}
          summary={(body) => {
            const value = body as Transfer;
            return (
              <ReviewSummary
                items={[
                  [
                    "Lot",
                    data.lots.find((lot) => lot.id === value.lot_id)
                      ?.external_code,
                  ],
                  [
                    "Kaynak",
                    data.locations.find(
                      (location) => location.id === value.from_location_id,
                    )?.name,
                  ],
                  [
                    "Hedef",
                    data.locations.find(
                      (location) => location.id === value.to_location_id,
                    )?.name,
                  ],
                  ["Miktar", amount(value.quantity) + " " + units[value.unit]],
                  ["Referans", value.reference || "Belirtilmedi"],
                ]}
              />
            );
          }}
          onSuccess={(result) => setCreated(result as Transfer)}
        >
          <TransferFields data={data} stocks={stocks} />
        </CommandForm>
      </Section>
      {created && (
        <Section title="Kaydedilen transfer ve güncel bakiyeler">
          <div className="stack">
            <RecordId id={created.id} label="Transfer kaydı" />
            <p>
              {amount(created.quantity)} {units[created.unit]} transfer kaydı ·{" "}
              {created.reference || "Referans belirtilmedi"}
            </p>
            <StockRows
              data={data}
              stocks={stocks.filter(
                (row) =>
                  row.lot_id === created.lot_id &&
                  [created.from_location_id, created.to_location_id].includes(
                    row.location_id,
                  ),
              )}
            />
          </div>
        </Section>
      )}
      <Section title="Transfer geçmişi">
        <State loading={records.isPending} error={records.error}>
          <Table readonlyReason="Kesin kayıt korunur. Düzeltme yalnız desteklenen iade, iptal veya yeni işlemle yapılır."
            headers={["Referans / tarih", "Lot", "Kaynak → hedef", "Miktar"]}
            empty={!records.data?.length}
          >
            {records.data?.map((row) => (
              <tr key={row.id}>
                <td>
                  {row.reference || "Referans yok"}
                  <small>{dateTime(row.transferred_at)}</small>
                  <RecordId id={row.id} />
                </td>
                <td>
                  <LotLink
                    id={row.lot_id}
                    code={
                      data.lots.find((lot) => lot.id === row.lot_id)
                        ?.external_code
                    }
                  />
                </td>
                <td>
                  {
                    data.locations.find(
                      (location) => location.id === row.from_location_id,
                    )?.name
                  }{" "}
                  →{" "}
                  {
                    data.locations.find(
                      (location) => location.id === row.to_location_id,
                    )?.name
                  }
                </td>
                <td>
                  {amount(row.quantity)} {units[row.unit]}
                </td>
              </tr>
            ))}
          </Table>
        </State>
      </Section>
    </div>
  );
}
export function CorrectionResult({
  record,
  data,
  stocks,
}: {
  record: Correction;
  data: Catalog;
  stocks: Stock[];
}) {
  return (
    <Section title="Kesin düzeltme kaydı">
      <div className="stack">
        <Badge tone="amber">Karantina · satılabilir değil</Badge>
        <ReviewSummary
          items={[
            ["Kayıtlı gelir düzeltmesi", eur(record.credit_amount)],
            ["Tarihsel maliyet düzeltmesi", eur(record.restored_cost)],
            [
              "Kabul konumu",
              data.locations.find(
                (location) => location.id === record.acceptance_location_id,
              )?.name,
            ],
          ]}
        />
        <p>{record.reason}</p>
        <p className="caption">
          Nakit geri ödeme kaydı yok. Orijinal satış geçmişi ve brüt tüketim
          sayaçları korunur.
        </p>
        <Link className="button" to={"/satislar/" + record.sale_id}>
          Kaynak satış ve net kârlılık
        </Link>
        <RecordId id={record.id} label="Düzeltme kaydı" />
        <StockRows
          data={data}
          stocks={stocks.filter(
            (row) =>
              row.location_id === record.acceptance_location_id &&
              record.lines?.some((line) => line.lot_id === row.lot_id),
          )}
        />
      </div>
    </Section>
  );
}
function ReturnFields({
  sales,
  shipments,
  data,
}: {
  sales: Sale[];
  shipments: ShipmentDetail[];
  data: Catalog;
}) {
  const { watch } = useFormContext();
  const chosen = shipments.filter(
    (shipment) => shipment.sale_id === watch("sale_id"),
  );
  return (
    <div className="form-grid">
      <Field name="sale_id" label="İade kaynak satışı">
        <option value="">Kayıtlı satış seçin</option>
        {sales
          .filter((sale) =>
            shipments.some((shipment) => shipment.sale_id === sale.id),
          )
          .map((sale) => (
            <option key={sale.id} value={sale.id}>
              {
                data.parties.find((party) => party.id === sale.customer_id)
                  ?.name
              }{" "}
              · {short(sale.id)} · {eur(sale.total_amount)}
            </option>
          ))}
      </Field>
      <Field name="shipment_line_id" label="İade sevkiyat satırı">
        <option value="">Kaynak satışın sevkiyat satırını seçin</option>
        {chosen.flatMap((shipment) =>
          shipment.lines.map((line) => (
            <option key={line.id} value={line.id}>
              {data.lots.find((lot) => lot.id === line.lot_id)?.external_code} ·{" "}
              {amount(line.quantity)} {units[line.unit]}
            </option>
          )),
        )}
      </Field>
      <Field name="quantity" label="İade miktarı" type="decimal" />
      <Field name="acceptance_location_id" label="Karantina kabul konumu">
        <Options
          items={data.locations.filter(
            (location) => location.kind === "quarantine",
          )}
        />
      </Field>
      <Field name="reason" label="İade nedeni" />
    </div>
  );
}
function Returns({
  data,
  stocks,
  initialSale,
}: {
  data: Catalog;
  stocks: Stock[];
  initialSale: string;
}) {
  const sales = useRecords<Sale>("/sales"),
    headers = useRecords<Shipment>("/shipments");
  const shipments = useRecordDetails<ShipmentDetail>(
    "/shipments",
    headers.data?.map((row) => row.id),
  );
  const returns = useRecords<Correction>("/returns");
  const [created, setCreated] = useState<Correction | null>(null),
    [selected, setSelected] = useState("");
  const detail = useQuery({
    queryKey: ["customer-return", selected],
    queryFn: () => request<Correction>("/returns/" + selected),
    enabled: !!selected,
    retry: false,
  });
  return (
    <State
      loading={sales.isPending || headers.isPending || shipments.isPending}
      error={sales.error || headers.error || shipments.error}
    >
      <div className="stack">
        <Section title="Müşteri iadesi">
          <CriticalNotice>
            Yalnız kayıtlı satışın bağlı sevkiyat satırı iade edilebilir. Ürün
            karantinaya alınır; otomatik satılabilir stok olmaz.
          </CriticalNotice>
          <CommandForm
            schema={returnSchema}
            defaults={{
              sale_id: initialSale,
              shipment_line_id: "",
              quantity: "",
              acceptance_location_id: "",
              reason: "",
            }}
            path="/returns"
            label="İadeyi gözden geçir"
            confirmText="Sevk edilmiş satırdan belirtilen miktar karantinaya kabul edilecek. Gelir ve tarihsel maliyet düzeltmesini backend kaydeder."
            payload={(value) => {
              const line = shipments
                .data!.flatMap((shipment) => shipment.lines)
                .find((row) => row.id === value.shipment_line_id)!;
              return {
                sale_id: value.sale_id,
                acceptance_location_id: value.acceptance_location_id,
                reason: value.reason,
                lines: [
                  {
                    sale_line_id: line.sale_line_id,
                    quantity: decimal(value.quantity),
                    unit: line.unit,
                  },
                ],
              };
            }}
            summary={(body) => {
              const value = body as {
                sale_id: string;
                acceptance_location_id: string;
                reason: string;
                lines: [
                  {
                    quantity: string;
                    unit: keyof typeof units;
                    sale_line_id: string;
                  },
                ];
              };
              return (
                <ReviewSummary
                  items={[
                    ["Kaynak satış", short(value.sale_id)],
                    [
                      "Kaynak lot",
                      data.lots.find(
                        (lot) =>
                          lot.id ===
                          shipments.data
                            ?.flatMap((shipment) => shipment.lines)
                            .find(
                              (line) =>
                                line.sale_line_id ===
                                value.lines[0].sale_line_id,
                            )?.lot_id,
                      )?.external_code,
                    ],
                    [
                      "Miktar",
                      amount(value.lines[0].quantity) +
                        " " +
                        units[value.lines[0].unit],
                    ],
                    [
                      "Karantina",
                      data.locations.find(
                        (location) =>
                          location.id === value.acceptance_location_id,
                      )?.name,
                    ],
                    ["Neden", value.reason],
                  ]}
                />
              );
            }}
            onSuccess={(result) => {
              setCreated(result as Correction);
              setSelected("");
            }}
          >
            <ReturnFields
              data={data}
              sales={sales.data || []}
              shipments={shipments.data || []}
            />
          </CommandForm>
        </Section>
        {(created || detail.data) && (
          <CorrectionResult
            record={(selected ? detail.data : created)!}
            data={data}
            stocks={stocks}
          />
        )}
        {selected && (
          <State loading={detail.isPending} error={detail.error}>
            {null}
          </State>
        )}
        <Section title="İade geçmişi">
          <State loading={returns.isPending} error={returns.error}>
            <Table readonlyReason="Kesin kayıt korunur. Düzeltme yalnız desteklenen iade, iptal veya yeni işlemle yapılır."
              headers={["Kayıt", "Gelir düzeltmesi", "Kabul", "Ayrıntı"]}
              empty={!returns.data?.length}
            >
              {returns.data?.map((row) => (
                <tr key={row.id}>
                  <td>
                    {row.reason}
                    <RecordId id={row.id} />
                  </td>
                  <td>{eur(row.credit_amount)}</td>
                  <td>Karantina</td>
                  <td>
                    <button
                      className="text-button"
                      onClick={() => {
                        setCreated(null);
                        setSelected(row.id);
                      }}
                    >
                      İadeyi aç
                    </button>
                  </td>
                </tr>
              ))}
            </Table>
          </State>
        </Section>
      </div>
    </State>
  );
}
function CancellationCheck() {
  const { register } = useFormContext();
  return (
    <>
      <label className="check-card">
        <input type="checkbox" {...register("acknowledged")} />
        Tam satışın iptal edileceğini ve ürünün karantinaya alınacağını anladım.
      </label>
      <ArrayError name="acknowledged" />
    </>
  );
}
function Cancellations({
  data,
  stocks,
  initialSale,
}: {
  data: Catalog;
  stocks: Stock[];
  initialSale: string;
}) {
  const [search, setSearch] = useSearchParams();
  const [created, setCreated] = useState<Correction | null>(null);
  const sales = useRecords<Sale>("/sales"),
    shipments = useRecords<Shipment>("/shipments");
  const saleId = search.get("sale") || initialSale;
  const mutating = useIsMutating();
  const profit = useQuery({
    queryKey: ["profitability", saleId],
    queryFn: () =>
      request<Profitability>("/sales/" + saleId + "/profitability"),
    enabled: !!saleId,
    retry: false,
  });
  const cancelled = useQuery({
    queryKey: ["cancellation", saleId],
    queryFn: () => request<Correction>("/sales/" + saleId + "/cancellation"),
    enabled: !!profit.data?.adjustments.cancellation_id,
    retry: false,
  });
  const shipped = shipments.data?.some(
    (shipment) => shipment.sale_id === saleId,
  );
  return (
    <State
      loading={sales.isPending || shipments.isPending}
      error={sales.error || shipments.error}
    >
      <div className="stack">
        <Section title="Sevk edilmemiş satışı iptal et">
          <CriticalNotice>
            Satış geçmişi silinmez. Tam ters kayıt ve karantina kabulü
            oluşturulur. Sevk edilmiş satış için müşteri iadesini kullanın.
          </CriticalNotice>
          <label className="field">
            İptal kaynak satışı
            <select
              value={saleId}
              disabled={
                !!mutating || !!loadPending("/sales/" + saleId + "/cancel")
              }
              onChange={(event) => {
                setCreated(null);
                setSearch({ islem: "iptal", sale: event.target.value });
              }}
            >
              <option value="">Satış seçin</option>
              {sales.data?.map((sale) => (
                <option
                  key={sale.id}
                  value={sale.id}
                  disabled={shipments.data?.some(
                    (shipment) => shipment.sale_id === sale.id,
                  )}
                >
                  {
                    data.parties.find((party) => party.id === sale.customer_id)
                      ?.name
                  }{" "}
                  · {short(sale.id)}
                  {shipments.data?.some(
                    (shipment) => shipment.sale_id === sale.id,
                  )
                    ? " · Sevk edildi"
                    : ""}
                </option>
              ))}
            </select>
          </label>
          {saleId && (
            <State loading={profit.isPending} error={profit.error}>
              {!loadPending("/sales/" + saleId + "/cancel") && shipped ? (
                <p role="alert" className="notice warning">
                  Bu satış sevk edilmiş; iptal yerine müşteri iadesi kullanın.
                </p>
              ) : !loadPending("/sales/" + saleId + "/cancel") &&
                profit.data?.adjustments.state !== "active" ? (
                <p className="caption">
                  Bu satışta zaten düzeltme var. Orijinal satış ve düzeltme
                  kayıtlarını inceleyin.
                </p>
              ) : (
                <CommandForm
                  key={saleId}
                  schema={cancelSchema}
                  defaults={{
                    acceptance_location_id: "",
                    reason: "",
                    acknowledged: false,
                  }}
                  path={"/sales/" + saleId + "/cancel"}
                  label="İptali gözden geçir"
                  confirmText="İKİNCİ ONAY: Satışın tamamı iptal edilecek ve ürün karantinaya alınacak. Nakit ödeme kaydı oluşturulmaz."
                  payload={(value) => ({
                    acceptance_location_id: value.acceptance_location_id,
                    reason: value.reason,
                  })}
                  summary={(body) => (
                    <ReviewSummary
                      items={[
                        ["Satış", short(saleId)],
                        [
                          "Orijinal kesin tutar",
                          eur(
                            sales.data?.find((sale) => sale.id === saleId)
                              ?.total_amount,
                          ),
                        ],
                        [
                          "Karantina",
                          data.locations.find(
                            (location) =>
                              location.id ===
                              (body as { acceptance_location_id: string })
                                .acceptance_location_id,
                          )?.name,
                        ],
                        ["Neden", (body as { reason: string }).reason],
                      ]}
                    />
                  )}
                  onSuccess={(result) => setCreated(result as Correction)}
                >
                  <div className="form-grid">
                    <Field
                      name="acceptance_location_id"
                      label="İptal karantina konumu"
                    >
                      <Options
                        items={data.locations.filter(
                          (location) => location.kind === "quarantine",
                        )}
                      />
                    </Field>
                    <Field name="reason" label="İptal nedeni" />
                  </div>
                  <CancellationCheck />
                </CommandForm>
              )}
            </State>
          )}
        </Section>
        {(created || cancelled.data) && (
          <CorrectionResult
            record={(created || cancelled.data)!}
            data={data}
            stocks={stocks}
          />
        )}
        {saleId && (
          <Link className="text-button" to={"/satislar/" + saleId}>
            Kaynak satış ve kârlılık
          </Link>
        )}
      </div>
    </State>
  );
}
export function Movements() {
  const [search] = useSearchParams();
  const selected = search.get("islem") || "transfer";
  const data = useCatalog(),
    stocks = useRecords<Stock>("/stocks");
  return (
    <State
      loading={data.loading || stocks.isPending}
      error={data.error || stocks.error}
    >
      <div className="stack">
        <ModuleIntro
          icon={<ArrowLeftRight size={24} />}
          title="Stok hareketleri, kesin kayıtlarla."
          description="Transfer, müşteri iadesi, satış iptali ve yeniden işleme. Bakiye ve maliyet yalnız backend onayıyla değişir."
        />
        <nav className="tabs" aria-label="Hareket türü">
          {[
            ["transfer", "Depo transferi"],
            ["iade", "Müşteri iadesi"],
            ["iptal", "Satış iptali"],
            ["rework", "Yeniden işleme"],
          ].map(([key, label]) => (
            <Link
              key={key}
              to={"/hareketler?islem=" + key}
              className={selected === key ? "active" : ""}
              aria-current={selected === key ? "page" : undefined}
            >
              {label}
            </Link>
          ))}
        </nav>
        {selected === "transfer" && (
          <Transfers data={data} stocks={stocks.data || []} />
        )}
        {selected === "iade" && (
          <Returns
            data={data}
            stocks={stocks.data || []}
            initialSale={search.get("sale") || ""}
          />
        )}
        {selected === "iptal" && (
          <Cancellations
            data={data}
            stocks={stocks.data || []}
            initialSale={search.get("sale") || ""}
          />
        )}
        {selected === "rework" && <Reworks />}
      </div>
    </State>
  );
}
