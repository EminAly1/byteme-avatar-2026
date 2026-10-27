import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useFieldArray, useFormContext } from "react-hook-form";
import { Plus, Trash2 } from "lucide-react";
import { z } from "zod";
import { CommandForm, Field, Options, ArrayError } from "../components/forms";
import { Section, State, Table } from "../components/ui";
import {
  CriticalNotice,
  LotLink,
  LotSelector,
  ProcessSteps,
  RecordId,
  ReviewSummary,
  StatusBadge,
} from "../components/workflow";
import { useCatalog, useRecords } from "../lib/data";
import { request } from "../lib/api";
import { loadPending } from "../lib/pending";
import { amount, decimal, eur } from "../lib/format";
import { balance } from "../lib/quantity";
import {
  reworkDraftSchema,
  reworkCloseSchema,
  reworkClosePayload,
} from "../lib/operational-validation";
import type { Rework } from "../lib/operational-types";
import type { Stock } from "../lib/types";

type Catalog = ReturnType<typeof useCatalog>;
function DraftFields({ data, stocks }: { data: Catalog; stocks: Stock[] }) {
  const { register } = useFormContext<z.infer<typeof reworkDraftSchema>>();
  const products = data.products.filter(
    (product) => product.base_unit === "kg" && product.type !== "raw",
  );
  return (
    <>
      <div className="form-grid">
        <Field name="code" label="Rework kodu" />
        <LotSelector
          name="source"
          label="Kaynak mamul lotu / depo"
          {...data}
          stocks={stocks.filter((stock) =>
            products.some((product) => product.id === stock.product_id),
          )}
        />
        <Field
          name="input_quantity"
          label="Rework girdi miktarı (kg)"
          type="decimal"
        />
        <Field name="reason" label="Yeniden işleme nedeni" />
      </div>
      <fieldset className="form-section">
        <legend>Planlanan çıktı ürünleri</legend>
        {products.map((product) => (
          <label className="check-card" key={product.id}>
            <input
              type="checkbox"
              value={product.id}
              {...register("output_product_ids")}
            />
            {product.name}
          </label>
        ))}
        <ArrayError name="output_product_ids" />
      </fieldset>
    </>
  );
}
export function Reworks() {
  const data = useCatalog(),
    stocks = useRecords<Stock>("/stocks"),
    records = useRecords<Rework>("/reworks");
  const navigate = useNavigate();
  return (
    <State
      loading={data.loading || stocks.isPending || records.isPending}
      error={data.error || stocks.error || records.error}
    >
      <div className="stack">
        <Section title="Yeniden işleme kayıtları">
          <ProcessSteps
            steps={["Taslak", "Fiilî çıktı ve hizmet", "Kesin kapanış"]}
            current={0}
          />
          <Table
            headers={["Rework", "Durum", "Kesin maliyet", "Ayrıntı"]}
            empty={!records.data?.length}
          >
            {records.data?.map((row) => (
              <tr key={row.id}>
                <td>{row.code}</td>
                <td>
                  <StatusBadge status={row.status} />
                </td>
                <td>
                  {row.status === "posted"
                    ? eur(row.total_cost)
                    : "Henüz muhasebeleşmedi"}
                </td>
                <td>
                  <Link
                    className="text-button"
                    to={"/hareketler/rework/" + row.id}
                  >
                    Rework kaydını aç
                  </Link>
                </td>
              </tr>
            ))}
          </Table>
        </Section>
        <Section title="Rework taslağı oluştur">
          <CriticalNotice>
            Taslak stok tüketmez. Yalnız daha önce üretilmiş uygun kg mamul/yan
            ürün kabul edilir; karantina için ayrı kalite onayı ve değerleme
            gerekir.
          </CriticalNotice>
          <CommandForm
            schema={reworkDraftSchema}
            defaults={{
              code: "",
              source: "",
              input_quantity: "",
              reason: "",
              output_product_ids: [],
            }}
            path="/reworks"
            label="Taslağı gözden geçir"
            confirmText="Yalnız rework planı oluşturulacak. Kaynak stok henüz tüketilmeyecek."
            payload={(value) => {
              const [source_lot_id, source_location_id] =
                value.source.split("|");
              return {
                code: value.code,
                source_lot_id,
                source_location_id,
                input_quantity: decimal(value.input_quantity),
                unit: "kg",
                reason: value.reason,
                output_product_ids: [...value.output_product_ids],
                service_costs: [],
              };
            }}
            summary={(body) => {
              const value = body as {
                code: string;
                source_lot_id: string;
                source_location_id: string;
                input_quantity: string;
                output_product_ids: string[];
              };
              return (
                <ReviewSummary
                  items={[
                    ["Kod", value.code],
                    [
                      "Kaynak",
                      data.lots.find((lot) => lot.id === value.source_lot_id)
                        ?.external_code,
                    ],
                    [
                      "Depo",
                      data.locations.find(
                        (location) => location.id === value.source_location_id,
                      )?.name,
                    ],
                    ["Girdi", amount(value.input_quantity) + " kg"],
                    [
                      "Çıktı ürünleri",
                      value.output_product_ids
                        .map(
                          (id) =>
                            data.products.find((product) => product.id === id)
                              ?.name,
                        )
                        .join(", "),
                    ],
                    ["Stok etkisi", "Taslakta stok ve kesin maliyet değişmez"],
                  ]}
                />
              );
            }}
            onSuccess={(result) =>
              navigate("/hareketler/rework/" + (result as Rework).id)
            }
          >
            <DraftFields data={data} stocks={stocks.data || []} />
          </CommandForm>
        </Section>
      </div>
    </State>
  );
}
function ClosingFields({ record, data }: { record: Rework; data: Catalog }) {
  type Values = z.infer<ReturnType<typeof reworkCloseSchema>>;
  const { control, watch } = useFormContext<Values>();
  const { fields, append, remove } = useFieldArray({
    control,
    name: "outputs",
  });
  const products = data.products.filter((product) =>
    record.allocation_snapshot.plan.output_product_ids.includes(product.id),
  );
  const current = watch();
  const summary = balance(
    record.allocation_snapshot.plan.input_quantity,
    current.outputs.map((row) => row.quantity),
    [current.loss_quantity],
  );
  return (
    <>
      <Field name="output_location_id" label="Rework çıktı deposu">
        <Options
          items={data.locations.filter(
            (location) => location.kind === "warehouse",
          )}
        />
      </Field>
      {fields.map((field, index) => (
        <fieldset className="line-card" key={field.id}>
          <legend>Çıktı {index + 1}</legend>
          <div className="form-grid">
            <Field
              name={`outputs.${index}.product_id`}
              label={`Çıktı ürünü ${index + 1}`}
            >
              <Options items={products} />
            </Field>
            <Field
              name={`outputs.${index}.lot_code`}
              label={`Yeni lot kodu ${index + 1}`}
            />
            <Field
              name={`outputs.${index}.quantity`}
              label={`Çıktı kg ${index + 1}`}
              type="decimal"
            />
            <Field
              name={`outputs.${index}.expires_at`}
              label={`Çıktı SKT ${index + 1}`}
              type="date"
              hint="Boşsa kaynak SKT miras alınır; uzatma kabul edilmez."
            />
            <Field
              name={`outputs.${index}.explanation`}
              label={`Çıktı açıklaması ${index + 1}`}
              hint="Yan ürün için zorunlu."
            />
          </div>
          <button
            className="button"
            type="button"
            disabled={fields.length === 1}
            onClick={() => remove(index)}
          >
            <Trash2 size={16} />
            Çıktı {index + 1} sil
          </button>
        </fieldset>
      ))}
      <ArrayError name="outputs" />
      <button
        className="button"
        type="button"
        disabled={fields.length >= 100}
        onClick={() =>
          append({
            product_id: products[0]?.id || "",
            lot_code: "",
            quantity: "",
            expires_at: "",
            explanation: "",
          })
        }
      >
        <Plus size={16} />
        Çıktı lotu ekle
      </button>
      <div className="form-grid">
        <Field
          name="loss_quantity"
          label="Açıklanmış kayıp (kg)"
          type="decimal"
        />
        <Field name="loss_kind" label="Kayıp türü">
          <option value="waste">Fire</option>
          <option value="other_loss">Diğer kayıp</option>
        </Field>
        <Field name="loss_reason" label="Kayıp nedeni" />
        <Field
          name="service_amount"
          label="Fiilî işlem bedeli (EUR)"
          type="decimal"
          hint="Gerçek kayıtlı bedel; AI tahmini değildir. Bedel yoksa 0."
        />
        <Field name="invoice_reference" label="Fiilî bedel belge referansı" />
      </div>
      {summary && (
        <p className={summary.balanced ? "notice success" : "notice warning"}>
          Girdi {amount(summary.input)} kg · Çıktı {amount(summary.output)} kg ·
          Açıklanmış kayıp {amount(summary.difference)} kg.{" "}
          {summary.balanced
            ? "Giriş özeti dengeli."
            : "Miktarları kontrol edin."}{" "}
          Kesin denetim backend'dedir.
        </p>
      )}
    </>
  );
}
export function ReworkPage() {
  const { id = "" } = useParams(),
    data = useCatalog();
  const query = useQuery({
    queryKey: ["rework", id],
    queryFn: () => request<Rework>("/reworks/" + id),
    retry: false,
  });
  const [posted, setPosted] = useState<Rework | null>(null);
  const record = posted?.id === id ? posted : query.data,
    path = "/reworks/" + id + "/post";
  return (
    <State
      loading={data.loading || query.isPending}
      error={data.error || query.error}
    >
      {record && (
        <div className="stack">
          <Link className="text-button" to="/hareketler?islem=rework">
            ← Rework kayıtları
          </Link>
          <Section title={record.code}>
            <div className="stack">
              <StatusBadge status={record.status} />
              <ProcessSteps
                steps={["Taslak", "Fiilî çıktı ve hizmet", "Kesin kapanış"]}
                current={record.status === "posted" ? 3 : 1}
              />
              <ReviewSummary
                items={[
                  [
                    "Kaynak lot",
                    <LotLink
                      id={record.allocation_snapshot.plan.source_lot_id}
                      code={
                        data.lots.find(
                          (lot) =>
                            lot.id ===
                            record.allocation_snapshot.plan.source_lot_id,
                        )?.external_code
                      }
                    />,
                  ],
                  [
                    "Planlanan girdi",
                    amount(record.allocation_snapshot.plan.input_quantity) +
                      " kg",
                  ],
                  ["Neden", record.allocation_snapshot.plan.reason],
                  [
                    "Kesin maliyet",
                    record.status === "posted"
                      ? eur(record.total_cost)
                      : "Henüz muhasebeleşmedi",
                  ],
                ]}
              />
              <RecordId id={record.id} label="Rework kaydı" />
            </div>
          </Section>
          {(record.status === "draft" || loadPending(path)) && (
            <Section title="Rework kesin kapanışı">
              <CriticalNotice>
                Onay kaynak stoğu tüketir ve yeni lotları gerçek maliyetle
                oluşturur. Taslak ayrı işlemdir. Karantina/blokaj/SKT ve miktar
                denetimleri backend'de tekrar yapılır.
              </CriticalNotice>
              <CommandForm
                key={id}
                schema={reworkCloseSchema(
                  record.allocation_snapshot.plan.input_quantity,
                )}
                defaults={{
                  output_location_id: "",
                  outputs:
                    record.allocation_snapshot.plan.output_product_ids.map(
                      (product_id) => ({
                        product_id,
                        lot_code: "",
                        quantity: "",
                        expires_at: "",
                        explanation: "",
                      }),
                    ),
                  loss_quantity: "0",
                  loss_kind: "other_loss",
                  loss_reason: "",
                  service_amount: "0",
                  invoice_reference: "",
                }}
                path={path}
                label="Kesin kapanışı gözden geçir"
                confirmText="KESİN KAPANIŞ: Kaynak lot tüketilecek; yeni çıktı lotları, fiilî hizmet bedelleri ve gerçek lot bağlantıları tek transaction'da kaydedilecek."
                payload={reworkClosePayload}
                onSuccess={(result) => setPosted(result as Rework)}
                summary={(body) => {
                  const value = body as ReturnType<typeof reworkClosePayload>;
                  return (
                    <div className="stack">
                      <ReviewSummary
                        items={[
                          [
                            "Kaynak girdi",
                            amount(
                              record.allocation_snapshot.plan.input_quantity,
                            ) + " kg",
                          ],
                          [
                            "Çıktı lotları",
                            value.outputs
                              .map(
                                (row) =>
                                  `${row.lot_code}: ${amount(row.quantity)} kg`,
                              )
                              .join("; "),
                          ],
                          [
                            "Açıklanmış kayıp",
                            value.differences.length
                              ? value.differences
                                  .map(
                                    (row) =>
                                      amount(row.quantity) +
                                      " kg · " +
                                      row.reason,
                                  )
                                  .join("; ")
                              : "0 kg",
                          ],
                          [
                            "Fiilî hizmet",
                            value.service_costs.length
                              ? eur(value.service_costs[0].amount)
                              : "0,00 €",
                          ],
                          [
                            "Maliyet kaynağı",
                            "Kesin defter tüketimi + kayıtlı fiilî hizmet; toplam backend kapanışından alınır",
                          ],
                        ]}
                      />
                    </div>
                  );
                }}
              >
                <ClosingFields record={record} data={data} />
              </CommandForm>
            </Section>
          )}
          {record.status === "posted" && (
            <Section title="Kesin rework çıktıları">
              <div className="stack">
                <p>
                  Kaynak maliyet payı: {eur(record.total_material_cost)} · Fiilî
                  hizmet: {eur(record.total_service_cost)} · Toplam:{" "}
                  <strong>{eur(record.total_cost)}</strong>
                </p>
                <Table
                  headers={["Yeni lot", "Miktar", "Kesin lot maliyeti", "SKT"]}
                  empty={!record.outputs.length}
                >
                  {record.outputs.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <LotLink id={row.lot_id} code={row.lot_code} />
                      </td>
                      <td>{amount(row.quantity)} kg</td>
                      <td>{eur(row.allocated_cost)}</td>
                      <td>{row.expires_at || "Kaydedilmemiş"}</td>
                    </tr>
                  ))}
                </Table>
              </div>
            </Section>
          )}
        </div>
      )}
    </State>
  );
}
