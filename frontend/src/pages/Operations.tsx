import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useFieldArray, useFormContext } from "react-hook-form";
import type { z } from "zod";
import { Plus, Trash2, ArrowRight, CheckCircle2 } from "lucide-react";
import { CommandForm, Field, Options, ArrayError } from "../components/forms";
import { Badge, Section, State, Table } from "../components/ui";
import { request } from "../lib/api";
import {
  operationPayload,
  dispatchPayload,
  closePayload,
} from "../lib/payloads";
import { useCatalog, useRecords } from "../lib/data";
import {
  operationSchema,
  dispatchSchema,
  closeSchema,
  cleanDecimal,
} from "../lib/validation";
import { amount, dateTime, eur, positive, short, units } from "../lib/format";
import type { Movement, Operation, OperationDetail, Stock } from "../lib/types";

export function Operations() {
  const data = useCatalog(),
    operations = useRecords<Operation>("/operations"),
    navigate = useNavigate();
  return (
    <State
      loading={data.loading || operations.isPending}
      error={data.error || operations.error}
    >
      <div className="stack">
        <Section
          title="Üretim emirleri"
          subtitle="Emir oluşturma, hammadde sevki ve fiilî kapanış ayrı adımlardır."
        >
          <Table
            headers={[
              "Emir",
              "Dış üretici",
              "Durum",
              "Gerçek toplam maliyet",
              "İşlem",
            ]}
            empty={!operations.data?.length}
          >
            {[
              ...(operations.data || []).filter(
                (x) => x.kind === "external_production",
              ),
            ]
              .sort((a, b) => b.created_at.localeCompare(a.created_at))
              .map((x) => (
                <tr key={x.id}>
                  <td className="code">{x.code}</td>
                  <td>
                    {data.parties.find((p) => p.id === x.producer_id)?.name}
                  </td>
                  <td>
                    <Badge tone={x.status === "posted" ? "green" : "amber"}>
                      {x.status === "posted" ? "Kapandı" : "Taslak / açık"}
                    </Badge>
                  </td>
                  <td>
                    {x.status === "posted"
                      ? eur(x.total_cost)
                      : "Kapanış bekleniyor"}
                  </td>
                  <td>
                    <Link className="text-button" to={"/uretim/" + x.id}>
                      Emri aç <ArrowRight size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
          </Table>
        </Section>
        <Section title="Dış üretim emri oluştur">
          <CommandForm<z.infer<typeof operationSchema>>
            schema={operationSchema}
            defaults={{ code: "", producer_id: "" }}
            path="/operations"
            label="Emri oluştur"
            confirmText="Taslak dış üretim emri oluşturulacak. Bu adım stok hareketi oluşturmaz."
            payload={operationPayload}
            onSuccess={(r) => navigate("/uretim/" + (r as Operation).id)}
          >
            <div className="form-grid">
              <Field name="code" label="Üretim emri numarası" />
              <Field name="producer_id" label="Dış üretici">
                <Options
                  items={data.parties.filter((x) =>
                    x.roles.includes("producer"),
                  )}
                />
              </Field>
            </div>
          </CommandForm>
        </Section>
      </div>
    </State>
  );
}

type Catalog = ReturnType<typeof useCatalog>;
function DispatchFields({
  data,
  stocks,
  producer,
}: {
  data: Catalog;
  stocks: Stock[];
  producer: string;
}) {
  const { control, watch } = useFormContext<z.infer<typeof dispatchSchema>>();
  const { fields, append, remove } = useFieldArray({ control, name: "lines" });
  const from = watch("from_location_id");
  const sourceStocks = stocks.filter(
    (x) =>
      x.location_id === from && positive(x.available_quantity) && !x.blocked,
  );
  return (
    <>
      <div className="form-grid">
        <Field name="from_location_id" label="Sevk çıkış deposu">
          <Options
            items={data.locations.filter((x) => x.kind === "warehouse")}
          />
        </Field>
        <Field name="to_location_id" label="Üretici kabul konumu">
          <Options
            items={data.locations.filter(
              (x) => x.kind === "external_producer" && x.party_id === producer,
            )}
          />
        </Field>
      </div>
      {fields.map((field, i) => (
        <div className="line-card" key={field.id}>
          <div className="line-title">
            <h4>Sevk satırı {i + 1}</h4>
            <button
              type="button"
              className="icon-button"
              aria-label={`Sevk satırı ${i + 1} sil`}
              disabled={fields.length === 1}
              onClick={() => remove(i)}
            >
              <Trash2 size={16} />
            </button>
          </div>
          <div className="form-grid">
            <Field name={`lines.${i}.lot_id`} label={`Sevk lotu ${i + 1}`}>
              <Options
                items={sourceStocks.map((s) => {
                  const lot = data.lots.find((l) => l.id === s.lot_id),
                    p = data.products.find((p) => p.id === s.product_id);
                  return {
                    id: s.lot_id,
                    name: `${lot?.external_code} · ${p?.name} · ${amount(s.available_quantity)} ${p && units[p.base_unit]} kullanılabilir`,
                  };
                })}
              />
            </Field>
            <Field
              name={`lines.${i}.quantity`}
              label={`Sevk miktarı ${i + 1}`}
              type="decimal"
            />
          </div>
        </div>
      ))}
      <ArrayError name="lines" />
      <button
        type="button"
        className="button"
        disabled={fields.length >= 100}
        onClick={() => append({ lot_id: "", quantity: "" })}
      >
        <Plus size={16} />
        Sevk satırı ekle
      </button>
      <p className="hint">
        Yalnızca seçilen depoda kullanılabilir stoğu olan lotlar listelenir.
        Birimler lotun ürün kartına bağlıdır.
      </p>
    </>
  );
}
interface Source {
  id: string;
  name: string;
}
function CloseFields({ data, sources }: { data: Catalog; sources: Source[] }) {
  const { control } = useFormContext<z.infer<typeof closeSchema>>();
  const consumed = useFieldArray({ control, name: "consumed_inputs" }),
    returned = useFieldArray({ control, name: "returned_inputs" }),
    outputs = useFieldArray({ control, name: "outputs" });
  return (
    <>
      <h3>Fiilî hammadde tüketimi</h3>
      <p className="hint">
        Sevk edilmiş her lotun tamamı tüketim veya iadeyle açıklanmalıdır.
        Miktarları fiilî sonuca göre girin.
      </p>
      {consumed.fields.map((field, i) => (
        <div className="line-card" key={field.id}>
          <div className="line-title">
            <h4>Tüketim satırı {i + 1}</h4>
            <button
              type="button"
              className="icon-button"
              aria-label={`Tüketim satırı ${i + 1} sil`}
              disabled={consumed.fields.length === 1}
              onClick={() => consumed.remove(i)}
            >
              <Trash2 size={16} />
            </button>
          </div>
          <div className="form-grid">
            <Field
              name={`consumed_inputs.${i}.source`}
              label={`Tüketilen lot / konum ${i + 1}`}
            >
              <Options items={sources} />
            </Field>
            <Field
              name={`consumed_inputs.${i}.quantity`}
              label={`Fiilî tüketim ${i + 1}`}
              type="decimal"
            />
          </div>
        </div>
      ))}
      <ArrayError name="consumed_inputs" />
      <button
        type="button"
        className="button"
        disabled={consumed.fields.length >= 100}
        onClick={() => consumed.append({ source: "", quantity: "" })}
      >
        <Plus size={16} />
        Tüketim satırı ekle
      </button>
      <h3>
        İade edilen hammaddeler <span className="optional">İsteğe bağlı</span>
      </h3>
      {returned.fields.map((field, i) => (
        <div className="line-card" key={field.id}>
          <div className="line-title">
            <h4>İade satırı {i + 1}</h4>
            <button
              type="button"
              className="icon-button"
              aria-label={`İade satırı ${i + 1} sil`}
              onClick={() => returned.remove(i)}
            >
              <Trash2 size={16} />
            </button>
          </div>
          <div className="form-grid cols-3">
            <Field
              name={`returned_inputs.${i}.source`}
              label={`İade lotu / konumu ${i + 1}`}
            >
              <Options items={sources} />
            </Field>
            <Field
              name={`returned_inputs.${i}.to_location_id`}
              label={`İade kabul deposu ${i + 1}`}
            >
              <Options
                items={data.locations.filter(
                  (x) => x.kind !== "external_producer",
                )}
              />
            </Field>
            <Field
              name={`returned_inputs.${i}.quantity`}
              label={`İade miktarı ${i + 1}`}
              type="decimal"
            />
          </div>
        </div>
      ))}
      <ArrayError name="returned_inputs" />
      <button
        type="button"
        className="button"
        disabled={returned.fields.length >= 100}
        onClick={() =>
          returned.append({ source: "", to_location_id: "", quantity: "" })
        }
      >
        <Plus size={16} />
        İade ekle
      </button>
      <h3>Mamul kabulü</h3>
      <Field name="output_location_id" label="Mamul kabul deposu">
        <Options items={data.locations.filter((x) => x.kind === "warehouse")} />
      </Field>
      {outputs.fields.map((field, i) => (
        <div className="line-card" key={field.id}>
          <div className="line-title">
            <h4>Mamul satırı {i + 1}</h4>
            <button
              type="button"
              className="icon-button"
              aria-label={`Mamul satırı ${i + 1} sil`}
              disabled={outputs.fields.length === 1}
              onClick={() => outputs.remove(i)}
            >
              <Trash2 size={16} />
            </button>
          </div>
          <div className="form-grid cols-3">
            <Field
              name={`outputs.${i}.product_id`}
              label={`Mamul ürün ${i + 1}`}
            >
              <Options
                items={data.products
                  .filter((x) => x.type !== "raw")
                  .map((x) => ({
                    id: x.id,
                    name: `${x.name} (${units[x.base_unit]})`,
                  }))}
              />
            </Field>
            <Field
              name={`outputs.${i}.lot_code`}
              label={`Mamul lot numarası ${i + 1}`}
            />
            <Field
              name={`outputs.${i}.quantity`}
              label={`Mamul miktarı ${i + 1}`}
              type="decimal"
            />
            <Field
              name={`outputs.${i}.expires_at`}
              label={`Mamul son tüketim tarihi ${i + 1}`}
              type="date"
            />
          </div>
        </div>
      ))}
      <ArrayError name="outputs" />
      <button
        type="button"
        className="button"
        disabled={outputs.fields.length >= 100}
        onClick={() =>
          outputs.append({
            product_id: "",
            lot_code: "",
            quantity: "",
            expires_at: "",
          })
        }
      >
        <Plus size={16} />
        Mamul satırı ekle
      </button>
      <h3>Hizmet ve miktar farkı</h3>
      <div className="form-grid">
        <Field
          name="service_amount"
          label="Toplam hizmet bedeli (EUR)"
          type="decimal"
          hint="Hammadde bedelini yeniden eklemeyin."
        />
        <Field name="invoice_reference" label="Hizmet faturası referansı" />
        <Field
          name="loss_quantity"
          label="Miktar farkı / fire (kg)"
          type="decimal"
        />
        <Field
          name="loss_reason"
          label="Miktar farkı açıklaması"
          hint="Fark pozitifse açıklama zorunlu."
        />
      </div>
      <p className="notice neutral">
        Ağırlık dengesi ve gerçek EKP backend tarafından doğrulanıp hesaplanır.
        Bu ekran tahmini maliyet üretmez.
      </p>
    </>
  );
}
export function OperationPage() {
  const { id } = useParams(),
    data = useCatalog(),
    detail = useQuery({
      queryKey: ["operation", id],
      queryFn: () => request<OperationDetail>("/operations/" + id),
      enabled: !!id,
      retry: false,
    }),
    stocks = useRecords<Stock>("/stocks"),
    moves = useRecords<Movement>("/stock-movements?operation_id=" + id);
  const op = detail.data,
    dispatched = (moves.data || []).filter((x) => x.type === "dispatch_in");
  const sources = Array.from(
    new Map(
      dispatched.map((x) => {
        const p = data.products.find(
          (p) => p.id === data.lots.find((l) => l.id === x.lot_id)?.product_id,
        );
        return [
          x.lot_id + "|" + x.location_id,
          {
            id: x.lot_id + "|" + x.location_id,
            name: `${data.lots.find((l) => l.id === x.lot_id)?.external_code} · ${p?.name} (${p && units[p.base_unit]}) · ${data.locations.find((l) => l.id === x.location_id)?.name}`,
          },
        ];
      }),
    ).values(),
  );
  if (op?.kind === "rework")
    return <Navigate replace to={"/hareketler/rework/" + op.id} />;
  if (op?.kind === "cutting")
    return <Navigate replace to={"/parcalama/" + op.id} />;
  return (
    <State
      loading={
        data.loading || detail.isPending || stocks.isPending || moves.isPending
      }
      error={data.error || detail.error || stocks.error || moves.error}
    >
      {op && (
        <div className="stack">
          <div className="operation-banner">
            <div>
              <Link to="/uretim" className="text-button">
                ← Üretim emirleri
              </Link>
              <h2>{op.code}</h2>
              <p>{data.parties.find((x) => x.id === op.producer_id)?.name}</p>
            </div>
            <Badge tone={op.status === "posted" ? "green" : "amber"}>
              {op.status === "posted" ? "Kapandı" : "Taslak / açık"}
            </Badge>
          </div>
          <div className="stepper">
            <span className="done">
              <CheckCircle2 size={18} />1 · Emir oluşturuldu
            </span>
            <span className={dispatched.length ? "done" : ""}>
              2 · Hammadde sevki
            </span>
            <span className={op.status === "posted" ? "done" : ""}>
              3 · Mamul kabulü ve kapanış
            </span>
          </div>
          {op.status === "posted" ? (
            <>
              <div className="stat-grid">
                <div className="stat">
                  <span>Hammadde maliyeti</span>
                  <strong>{eur(op.total_material_cost)}</strong>
                </div>
                <div className="stat">
                  <span>Hizmet maliyeti</span>
                  <strong>{eur(op.total_service_cost)}</strong>
                </div>
                <div className="stat accent">
                  <span>Gerçek toplam maliyet</span>
                  <strong>{eur(op.total_cost_display)}</strong>
                </div>
                <div className="stat">
                  <span>Kayıtlı miktar farkı</span>
                  <strong>{amount(op.loss_quantity)} kg</strong>
                </div>
              </div>
              <Section
                title="Mamul kabulü ve EKP"
                subtitle={
                  op.posted_at
                    ? "Kapanış: " + dateTime(op.posted_at)
                    : undefined
                }
              >
                <Table
                  headers={[
                    "Mamul lotu",
                    "Miktar",
                    "Dağıtılan maliyet",
                    "Birim EKP (gösterim)",
                  ]}
                  empty={!op.outputs.length}
                >
                  {op.outputs.map((x) => {
                    const lot = data.lots.find((l) => l.id === x.lot_id),
                      p = data.products.find((p) => p.id === lot?.product_id);
                    return (
                      <tr key={x.id}>
                        <td className="code">
                          {lot?.external_code || short(x.lot_id)}
                        </td>
                        <td>
                          {amount(x.quantity)} {p && units[p.base_unit]}
                        </td>
                        <td>{eur(x.allocated_cost)}</td>
                        <td className="strong">{eur(x.unit_cost_display)}</td>
                      </tr>
                    );
                  })}
                </Table>
                <p className="table-foot">
                  EKP backend sonucudur. Gösterilen birim maliyet
                  yuvarlanmıştır; toplam tutar bununla yeniden hesaplanmaz.
                </p>
              </Section>
              <Section
                title="Kayıtlı kaynak lot bağlantıları"
                subtitle="Bu emrin kesin girdi–çıktı kayıtları; tam ileri/geri izleme modülü değildir."
              >
                <Table
                  headers={[
                    "Kaynak lot",
                    "Mamul lot",
                    "İlişkilendirilen girdi miktarı",
                  ]}
                  empty={!op.lot_links.length}
                >
                  {op.lot_links.map((x) => (
                    <tr key={x.id}>
                      <td className="code">
                        {data.lots.find((l) => l.id === x.input_lot_id)
                          ?.external_code || short(x.input_lot_id)}
                      </td>
                      <td className="code">
                        {data.lots.find((l) => l.id === x.output_lot_id)
                          ?.external_code || short(x.output_lot_id)}
                      </td>
                      <td>
                        {amount(x.attributed_input_quantity)}{" "}
                        {
                          units[
                            data.products.find(
                              (p) =>
                                p.id ===
                                data.lots.find((l) => l.id === x.input_lot_id)
                                  ?.product_id,
                            )?.base_unit || "kg"
                          ]
                        }
                      </td>
                    </tr>
                  ))}
                </Table>
                {op.loss_reason && (
                  <p className="table-foot">
                    Miktar farkı açıklaması: {op.loss_reason}
                  </p>
                )}
              </Section>
            </>
          ) : (
            <>
              <Section
                title="Hammadde sevki"
                subtitle="Sevk mülkiyeti değiştirmez ve henüz tüketim maliyeti oluşturmaz."
              >
                <CommandForm<z.infer<typeof dispatchSchema>>
                  schema={dispatchSchema}
                  defaults={{
                    from_location_id: "",
                    to_location_id: "",
                    lines: [{ lot_id: "", quantity: "" }],
                  }}
                  path={"/operations/" + id + "/dispatch"}
                  label="Hammadde sevkini kaydet"
                  confirmText="Seçilen hammaddeler işletme deposundan dış üretici konumuna aktarılacak."
                  payload={dispatchPayload}
                >
                  <DispatchFields
                    data={data}
                    stocks={stocks.data || []}
                    producer={op.producer_id || ""}
                  />
                </CommandForm>
              </Section>
              <Section title="Bu emre kaydedilen sevkler">
                <Table
                  headers={["Lot", "Üretici konumu", "Sevk miktarı", "Tarih"]}
                  empty={!dispatched.length}
                >
                  {dispatched.map((x) => (
                    <tr key={x.id}>
                      <td className="code">
                        {data.lots.find((l) => l.id === x.lot_id)
                          ?.external_code || short(x.lot_id)}
                      </td>
                      <td>
                        {
                          data.locations.find((l) => l.id === x.location_id)
                            ?.name
                        }
                      </td>
                      <td>{amount(x.quantity)}</td>
                      <td>{dateTime(x.created_at)}</td>
                    </tr>
                  ))}
                </Table>
              </Section>
              {sources.length > 0 ? (
                <Section
                  title="Mamul kabulü ve üretim kapanışı"
                  subtitle="Kapanıştan sonra emir değiştirilemez."
                >
                  <CommandForm<z.infer<typeof closeSchema>>
                    schema={closeSchema}
                    defaults={{
                      consumed_inputs: [{ source: "", quantity: "" }],
                      returned_inputs: [],
                      output_location_id: "",
                      outputs: [
                        {
                          product_id: "",
                          lot_code: "",
                          quantity: "",
                          expires_at: "",
                        },
                      ],
                      service_amount: "0.00",
                      invoice_reference: "",
                      loss_quantity: "0",
                      loss_reason: "",
                    }}
                    path={"/operations/" + id + "/post"}
                    label="Üretimi kapat"
                    confirmText="Fiilî tüketim, iadeler, mamul stokları, maliyet ve lot bağlantıları birlikte kaydedilecek. Kapanmış emir bu sürümde değiştirilemez."
                    payload={closePayload}
                  >
                    <CloseFields data={data} sources={sources} />
                  </CommandForm>
                </Section>
              ) : (
                <p className="notice neutral">
                  Mamul kabulünden önce hammadde sevkini kaydedin.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </State>
  );
}
