import { useState } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useFieldArray, useFormContext } from "react-hook-form";
import { z } from "zod";
import { Plus, ShoppingBag, Truck, Trash2 } from "lucide-react";
import { CommandForm, Field, Options, ArrayError } from "../components/forms";
import { Badge, Section, State, Table, Empty } from "../components/ui";
import {
  DetailDrawer,
  FilterBar,
  LotSelector,
  LotLink,
  ModuleIntro,
  NumberInput,
  RecordId,
  ReviewSummary,
  StatCard,
  CriticalNotice,
} from "../components/workflow";
import { useCatalog, useRecords, useRecordDetails } from "../lib/data";
import { request } from "../lib/api";
import { loadPending } from "../lib/pending";
import { amount, dateTime, eur, short, units } from "../lib/format";
import type { Stock } from "../lib/types";
import type {
  Sale,
  SaleDetail,
  Shipment,
  ShipmentDetail,
} from "../lib/modules";
import {
  saleSchema,
  independentShipmentSchema,
} from "../lib/module-validation";
import { id } from "../lib/validation";
import {
  salePayload,
  shipmentPayload,
  linkedShipmentPayload,
} from "../lib/module-payloads";

type Catalog = ReturnType<typeof useCatalog>;
function TradeLines({
  data,
  stocks,
  price = true,
}: {
  data: Catalog;
  stocks: Stock[];
  price?: boolean;
}) {
  const { control } = useFormContext<{
    customer_id: string;
    lines: Array<{ source: string; quantity: string; unit_price: string }>;
  }>();
  const { fields, append, remove } = useFieldArray({ control, name: "lines" });
  return (
    <>
      <div className="form-grid">
        <Field name="customer_id" label="Müşteri">
          <Options
            items={data.parties.filter((p) => p.roles.includes("customer"))}
          />
        </Field>
      </div>
      {fields.map((f, i) => (
        <div className="line-card" key={f.id}>
          <div className="line-title">
            <h4>
              {price ? "Satış" : "Sevk"} satırı {i + 1}
            </h4>
            <button
              className="icon-button"
              type="button"
              aria-label={`İşlem satırı ${i + 1} sil`}
              disabled={fields.length === 1}
              onClick={() => remove(i)}
            >
              <Trash2 size={17} />
            </button>
          </div>
          <div className="form-grid">
            <LotSelector
              name={`lines.${i}.source`}
              label={`Lot / konum ${i + 1}`}
              stocks={stocks}
              {...data}
            />
            <NumberInput
              name={`lines.${i}.quantity`}
              label={`Miktar ${i + 1}`}
              hint="Lot ürününün stok birimi kullanılır; adet/paket tam sayı olmalıdır."
            />
            {price && (
              <NumberInput
                name={`lines.${i}.unit_price`}
                label={`Birim fiyat ${i + 1} (EUR)`}
              />
            )}
          </div>
        </div>
      ))}
      <ArrayError name="lines" />
      <button
        className="button"
        type="button"
        onClick={() => append({ source: "", quantity: "", unit_price: "" })}
      >
        <Plus size={16} />
        İşlem satırı ekle
      </button>
    </>
  );
}
function TradeSummary({ body, data }: { body: unknown; data: Catalog }) {
  const b = body as {
    customer_id: string;
    lines: Array<{
      lot_id: string;
      location_id: string;
      quantity: string;
      unit_price?: string;
    }>;
  };
  return (
    <>
      <ReviewSummary
        items={[
          [
            "Müşteri",
            data.parties.find((p) => p.id === b.customer_id)?.name ||
              b.customer_id,
          ],
        ]}
      />
      <div className="record-list">
        {b.lines.map((l, i) => (
          <div key={i} className="review-line">
            <strong>
              {data.lots.find((x) => x.id === l.lot_id)?.external_code ||
                l.lot_id}
            </strong>
            <p>
              {data.locations.find((x) => x.id === l.location_id)?.name} ·{" "}
              {amount(l.quantity)}{" "}
              {
                units[
                  data.products.find(
                    (p) =>
                      p.id ===
                      data.lots.find((x) => x.id === l.lot_id)?.product_id,
                  )?.base_unit || "unit"
                ]
              }
              {l.unit_price ? " · " + eur(l.unit_price) + " / birim" : ""}
            </p>
          </div>
        ))}
      </div>
      <p className="caption">
        Kesin tutar ve stok hareketi backend onayından sonra gösterilir.
      </p>
    </>
  );
}
function LinesTable({
  record,
  data,
  shipment = false,
}: {
  record: SaleDetail | ShipmentDetail;
  data: Catalog;
  shipment?: boolean;
}) {
  return (
    <Table
      headers={[
        "Ürün / lot",
        "Konum",
        "Miktar",
        ...(shipment ? [] : ["Birim fiyat", "Satır tutarı"]),
        "Stok hareketi",
      ]}
      empty={!record.lines.length}
    >
      {record.lines.map((l) => (
        <tr key={l.id}>
          <td>
            <strong>
              {data.products.find((p) => p.id === l.product_id)?.name}
            </strong>
            <LotLink
              id={l.lot_id}
              code={data.lots.find((x) => x.id === l.lot_id)?.external_code}
            />
            <small className="code">Satır: {l.id}</small>
          </td>
          <td>{data.locations.find((x) => x.id === l.location_id)?.name}</td>
          <td>
            {amount(l.quantity)} {units[l.unit]}
          </td>
          {!shipment && (
            <>
              <td>{eur((l as SaleDetail["lines"][number]).unit_price)}</td>
              <td>{eur((l as SaleDetail["lines"][number]).total_amount)}</td>
            </>
          )}
          <td className="code">{l.stock_movement_id}</td>
        </tr>
      ))}
    </Table>
  );
}
export function Sales() {
  const data = useCatalog(),
    stocks = useRecords<Stock>("/stocks"),
    headers = useRecords<Sale>("/sales"),
    records = useRecordDetails<SaleDetail>(
      "/sales",
      headers.data?.map((x) => x.id),
    ),
    navigate = useNavigate();
  const [customer, setCustomer] = useState(""),
    [lot, setLot] = useState(""),
    [creating, setCreating] = useState(!!loadPending("/sales"));
  const filtered =
    records.data?.filter(
      (s) =>
        (!customer || s.customer_id === customer) &&
        (!lot || s.lines.some((l) => l.lot_id === lot)),
    ) || [];
  return (
    <State
      loading={
        data.loading ||
        stocks.isPending ||
        headers.isPending ||
        records.isPending
      }
      error={data.error || stocks.error || headers.error || records.error}
    >
      <div className="stack">
        <ModuleIntro
          title="Her satış, kesin bir lot kaydı."
          description="Müşteriyi ve kullanılabilir lotu seçin. Stok yalnız backend kesin onayıyla bir kez düşer."
          icon={<ShoppingBag size={24} />}
        />
        <Section
          title="Satış geçmişi"
          subtitle="Tutarlar ve hareket kimlikleri gerçek API kayıtlarıdır."
          action={
            <button
              className="button primary"
              onClick={() => setCreating(!creating)}
            >
              {creating ? "Formu kapat" : "Yeni satış"}
            </button>
          }
        >
          <div hidden={creating}>
            <FilterBar>
              <label>
                Müşteri filtresi
                <select
                  aria-label="Müşteri filtresi"
                  value={customer}
                  onChange={(e) => setCustomer(e.target.value)}
                >
                  <option value="">Tüm müşteriler</option>
                  {data.parties
                    .filter((p) => p.roles.includes("customer"))
                    .map((p) => (
                      <option value={p.id} key={p.id}>
                        {p.name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Satış lot filtresi
                <select
                  aria-label="Satış lot filtresi"
                  value={lot}
                  onChange={(e) => setLot(e.target.value)}
                >
                  <option value="">Tüm lotlar</option>
                  {data.lots.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.external_code}
                    </option>
                  ))}
                </select>
              </label>
            </FilterBar>
            <Table
              headers={[
                "Tarih / satış",
                "Müşteri",
                "Lot satırı",
                "Kesin tutar",
                "Ayrıntı",
              ]}
              empty={!filtered.length}
            >
              {filtered.map((s) => (
                <tr key={s.id}>
                  <td>
                    {dateTime(s.sold_at)}
                    <small className="code">{short(s.id)}</small>
                  </td>
                  <td>
                    {data.parties.find((p) => p.id === s.customer_id)?.name}
                  </td>
                  <td>{s.lines.length}</td>
                  <td>{eur(s.total_amount)}</td>
                  <td>
                    <Link className="text-button" to={"/satislar/" + s.id}>
                      Satışı aç
                    </Link>
                  </td>
                </tr>
              ))}
            </Table>
          </div>
          {creating && (
            <p className="caption">
              Yeni satış formu aşağıda. Geçmişe dönmek için formu kapatın.
            </p>
          )}
        </Section>
        {creating && (
          <Section title="Lotlu satış oluştur">
            <CommandForm
              schema={saleSchema}
              defaults={{
                customer_id: "",
                lines: [{ source: "", quantity: "", unit_price: "" }],
              }}
              path="/sales"
              label="Satışı gözden geçir"
              confirmText="Bu bir kesin satıştır. Onaydan sonra seçilen lotlardan stok ve gerçek maliyet çıkışı kaydedilir."
              payload={salePayload}
              summary={(b) => <TradeSummary body={b} data={data} />}
              onSuccess={(r) => navigate("/satislar/" + (r as Sale).id)}
            >
              <TradeLines data={data} stocks={stocks.data || []} />
            </CommandForm>
          </Section>
        )}
      </div>
    </State>
  );
}
export function SalePage() {
  const { id: recordId = "" } = useParams(),
    data = useCatalog(),
    q = useQuery({
      queryKey: ["sale", recordId],
      queryFn: () => request<SaleDetail>("/sales/" + recordId),
      retry: false,
    });
  const s = q.data;
  return (
    <State loading={data.loading || q.isPending} error={data.error || q.error}>
      {s && (
        <div className="stack">
          <Link className="text-button" to="/satislar">
            ← Satış geçmişi
          </Link>
          <div className="detail-heading">
            <h2>{data.parties.find((p) => p.id === s.customer_id)?.name}</h2>
            <Badge tone="green">Kesin satış</Badge>
          </div>
          <RecordId id={s.id} label="Satış UUID" />
          <div className="stat-grid">
            <StatCard label="Kesin satış tutarı" value={eur(s.total_amount)} />
            <StatCard label="Satış tarihi" value={dateTime(s.sold_at)} />
            <StatCard label="Lot satırı" value={s.lines.length} />
          </div>
          <Section title="Satış satırları ve stok hareketleri">
            <LinesTable record={s} data={data} />
          </Section>
          <Link className="button primary" to={"/sevkiyatlar?sale=" + s.id}>
            Bu satışa bağlı sevkiyat oluştur
          </Link>
          <CriticalNotice>
            Satış stoku zaten düşürdü. Bağlı sevkiyat aynı hareketi referans
            alır; ikinci stok çıkışı yapmaz.
          </CriticalNotice>
        </div>
      )}
    </State>
  );
}
const linkedSchema = z.object({
  line_ids: z.array(id).min(1, "En az bir sevk edilmemiş satış satırı seçin."),
});
function LinkedFields({
  sale,
  shipped,
  data,
}: {
  sale: SaleDetail;
  shipped: Set<string>;
  data: Catalog;
}) {
  const { register } = useFormContext<z.infer<typeof linkedSchema>>();
  return (
    <>
      <p className="caption">
        Yalnız sevk edilmemiş tam satış satırları seçilir. Miktar ve müşteri
        kesin satış kaydından alınır.
      </p>
      {sale.lines.map((l) => (
        <label className="check-card" key={l.id}>
          <input
            type="checkbox"
            value={l.id}
            {...register("line_ids")}
            disabled={shipped.has(l.id)}
          />
          <span>
            <strong>
              {data.lots.find((x) => x.id === l.lot_id)?.external_code}
            </strong>
            <small>
              {amount(l.quantity)} {units[l.unit]} ·{" "}
              {shipped.has(l.id) ? "Zaten sevk edildi" : "Sevk bekliyor"}
            </small>
          </span>
        </label>
      ))}
      <ArrayError name="line_ids" />
    </>
  );
}
export function Shipments() {
  const [search] = useSearchParams(),
    data = useCatalog(),
    stocks = useRecords<Stock>("/stocks"),
    sales = useRecords<Sale>("/sales"),
    headers = useRecords<Shipment>("/shipments"),
    records = useRecordDetails<ShipmentDetail>(
      "/shipments",
      headers.data?.map((x) => x.id),
    );
  const pending = loadPending("/shipments"),
    initialLinked = !!(
      pending?.command.body as { sale_id?: string } | undefined
    )?.sale_id;
  const [mode, setMode] = useState<"linked" | "independent">(
      search.get("sale") || initialLinked ? "linked" : "independent",
    ),
    [saleId, setSaleId] = useState(
      search.get("sale") ||
        (pending?.command.body as { sale_id?: string } | undefined)?.sale_id ||
        "",
    ),
    [selected, setSelected] = useState(search.get("shipment") || ""),
    [customer, setCustomer] = useState(""),
    [lot, setLot] = useState(""),
    [notice, setNotice] = useState("");
  const sale = useQuery({
    queryKey: ["sale", saleId],
    queryFn: () => request<SaleDetail>("/sales/" + saleId),
    enabled: !!saleId,
    retry: false,
  });
  const detail = records.data?.find((s) => s.id === selected);
  const shipped = new Set(
    records.data?.flatMap((s) =>
      s.lines.map((l) => l.sale_line_id).filter((id): id is string => !!id),
    ) || [],
  );
  const [created, setCreated] = useState<ShipmentDetail | null>(null);
  const filtered =
    records.data?.filter(
      (s) =>
        (!customer || s.customer_id === customer) &&
        (!lot || s.lines.some((l) => l.lot_id === lot)),
    ) || [];
  function changeMode(next: "linked" | "independent") {
    if (loadPending("/shipments")) {
      setNotice(
        "Sonucu belirsiz mevcut sevkiyatı aynı anahtarla tamamlamadan tür değiştiremezsiniz.",
      );
      return;
    }
    setMode(next);
    setNotice("");
  }
  return (
    <State
      loading={
        data.loading ||
        stocks.isPending ||
        headers.isPending ||
        records.isPending ||
        sales.isPending
      }
      error={
        data.error ||
        stocks.error ||
        headers.error ||
        records.error ||
        sales.error
      }
    >
      <div className="stack">
        <ModuleIntro
          title="Teslimatlar kayıt altında."
          description="Bağımsız stok çıkışı ile satışın teslim belgesini ayrı yönetin. Market kalanı kaydedilmediyse bilinmez."
          icon={<Truck size={24} />}
        />
        <Section title="Market sevkiyatları">
          <FilterBar>
            <label>
              Müşteri filtresi
              <select
                aria-label="Müşteri filtresi"
                value={customer}
                onChange={(e) => setCustomer(e.target.value)}
              >
                <option value="">Tüm müşteriler</option>
                {data.parties
                  .filter((p) => p.roles.includes("customer"))
                  .map((p) => (
                    <option value={p.id} key={p.id}>
                      {p.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Sevkiyat lot filtresi
              <select
                aria-label="Sevkiyat lot filtresi"
                value={lot}
                onChange={(e) => setLot(e.target.value)}
              >
                <option value="">Tüm lotlar</option>
                {data.lots.map((l) => (
                  <option value={l.id} key={l.id}>
                    {l.external_code}
                  </option>
                ))}
              </select>
            </label>
          </FilterBar>
          <Table
            headers={[
              "Tarih",
              "Market / alıcı",
              "Lot ve miktar",
              "Tür",
              "Market kalanı",
              "Ayrıntı",
            ]}
            empty={!filtered.length}
          >
            {filtered.map((s) => (
              <tr key={s.id}>
                <td>{dateTime(s.shipped_at)}</td>
                <td>
                  <strong>{s.recipient_name}</strong>
                  <small>{s.recipient_contact || "İletişim kaydı yok"}</small>
                </td>
                <td>
                  {s.lines.map((l) => (
                    <div key={l.id}>
                      {data.lots.find((x) => x.id === l.lot_id)?.external_code}{" "}
                      · {amount(l.quantity)} {units[l.unit]}
                    </div>
                  ))}
                </td>
                <td>
                  <Badge tone={s.sale_id ? "green" : ""}>
                    {s.sale_id ? "Satışa bağlı" : "Bağımsız çıkış"}
                  </Badge>
                </td>
                <td>Bilinmiyor</td>
                <td>
                  <button
                    className="text-button"
                    onClick={() => setSelected(s.id)}
                  >
                    Sevkiyatı aç
                  </button>
                </td>
              </tr>
            ))}
          </Table>
        </Section>
        <Section title="Sevkiyat oluştur">
          <div className="tabs" role="group" aria-label="Sevkiyat türü">
            <button
              className={mode === "independent" ? "active" : ""}
              onClick={() => changeMode("independent")}
            >
              Bağımsız sevkiyat
            </button>
            <button
              className={mode === "linked" ? "active" : ""}
              onClick={() => changeMode("linked")}
            >
              Satışa bağlı sevkiyat
            </button>
          </div>
          {notice && (
            <p role="alert" className="field-error">
              {notice}
            </p>
          )}
          {mode === "independent" ? (
            <>
              <CriticalNotice>
                Bağımsız sevkiyat fiziksel stok çıkışıdır. Satış/fatura ve gelir
                kaydı oluşturmaz.
              </CriticalNotice>
              <CommandForm
                key="independent"
                schema={independentShipmentSchema}
                defaults={{
                  customer_id: "",
                  lines: [{ source: "", quantity: "" }],
                }}
                path="/shipments"
                label="Bağımsız sevkiyatı gözden geçir"
                confirmText="Seçili lotlardan yeni bir fiziksel stok çıkışı kaydedilecek."
                payload={shipmentPayload}
                summary={(b) => <TradeSummary body={b} data={data} />}
                onSuccess={(r) => {
                  setCreated(r as ShipmentDetail);
                  setSelected((r as Shipment).id);
                }}
              >
                <TradeLines
                  data={data}
                  stocks={stocks.data || []}
                  price={false}
                />
              </CommandForm>
            </>
          ) : (
            <>
              <CriticalNotice>
                Bağlı sevkiyat satışın stok hareketini paylaşır. Stok ikinci kez
                düşmez.
              </CriticalNotice>
              <label className="field">
                Bağlı satış
                <select
                  aria-label="Bağlı satış"
                  value={saleId}
                  onChange={(e) => {
                    if (loadPending("/shipments")) return;
                    setSaleId(e.target.value);
                  }}
                >
                  <option value="">Satış seçin</option>
                  {sales.data?.map((s) => (
                    <option value={s.id} key={s.id}>
                      {data.parties.find((p) => p.id === s.customer_id)?.name} ·{" "}
                      {dateTime(s.sold_at)} · {short(s.id)}
                    </option>
                  ))}
                </select>
              </label>
              {saleId && (
                <State loading={sale.isPending} error={sale.error}>
                  {sale.data && (
                    <CommandForm
                      key={saleId}
                      schema={linkedSchema}
                      defaults={{
                        line_ids: sale.data.lines
                          .filter((l) => !shipped.has(l.id))
                          .map((l) => l.id),
                      }}
                      path="/shipments"
                      label="Bağlı sevkiyatı gözden geçir"
                      confirmText="Tam satış satırları teslim belgesine bağlanacak; yeni stok çıkışı yapılmayacak."
                      payload={(v) =>
                        linkedShipmentPayload(sale.data!, v.line_ids)
                      }
                      summary={(b) => <TradeSummary body={b} data={data} />}
                      onSuccess={(r) => {
                        setCreated(r as ShipmentDetail);
                        setSelected((r as Shipment).id);
                      }}
                    >
                      <LinkedFields
                        sale={sale.data}
                        shipped={shipped}
                        data={data}
                      />
                    </CommandForm>
                  )}
                </State>
              )}
            </>
          )}
        </Section>
        {selected && (detail || created?.id === selected) && (
          <DetailDrawer
            title="Sevkiyat ayrıntısı"
            onClose={() => setSelected("")}
          >
            <div className="stack">
              <RecordId id={selected} label="Sevkiyat UUID" />
              <p>{(detail || created)!.recipient_name}</p>
              {(detail || created)!.sale_id && (
                <Link
                  className="text-button"
                  to={"/satislar/" + (detail || created)!.sale_id}
                >
                  Bağlı satışı aç
                </Link>
              )}
              <p>
                Market kalanı: <strong>Bilinmiyor</strong>
              </p>
              <LinesTable record={(detail || created)!} data={data} shipment />
            </div>
          </DetailDrawer>
        )}
      </div>
    </State>
  );
}
