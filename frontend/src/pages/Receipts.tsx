import { useState } from "react";
import { useFieldArray, useFormContext } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";
import type { z } from "zod";
import { Plus, Trash2 } from "lucide-react";
import { CommandForm, Field, Options } from "../components/forms";
import { DetailDrawer } from "../components/dialogs";
import { RecordId } from "../components/presentation";
import { Section, State, Table, Success } from "../components/ui";
import { useCatalog, useRecords } from "../lib/data";
import { request } from "../lib/api";
import { receiptPayload } from "../lib/payloads";
import { receiptSchema, cleanDecimal } from "../lib/validation";
import { amount, dateTime, eur, units } from "../lib/format";
import type { Receipt, ReceiptDetail } from "../lib/types";

const blankLine = {
  product_id: "",
  external_lot_code: "",
  quantity: "",
  total_cost: "",
  expires_at: "",
};
function ReceiptFields({ data }: { data: ReturnType<typeof useCatalog> }) {
  const { control, watch } = useFormContext<z.infer<typeof receiptSchema>>();
  const lines = watch("lines");
  const { fields, append, remove } = useFieldArray({ control, name: "lines" });
  return (
    <>
      <div className="form-grid">
        <Field name="supplier_id" label="Tedarikçi">
          <Options
            items={data.parties.filter((x) => x.roles.includes("supplier"))}
          />
        </Field>
        <Field name="location_id" label="Kabul deposu">
          <Options
            items={data.locations.filter((x) => x.kind !== "external_producer")}
          />
        </Field>
        <Field name="reference" label="Belge / alış referansı" />
      </div>
      <h3>Alış satırları</h3>
      {fields.map((field, i) => (
        <div className="line-card" key={field.id}>
          <div className="line-title">
            <h4>Lot girişi {i + 1}</h4>
            <button
              type="button"
              className="icon-button"
              aria-label={`Alış satırı ${i + 1} sil`}
              disabled={fields.length === 1}
              onClick={() => remove(i)}
            >
              <Trash2 size={16} />
            </button>
          </div>
          <div className="form-grid">
            <Field name={`lines.${i}.product_id`} label={`Ürün ${i + 1}`}>
              <Options
                items={data.products.map((x) => ({
                  id: x.id,
                  name: `${x.sku} · ${x.name} (${units[x.base_unit]})`,
                }))}
              />
            </Field>
            <Field
              name={`lines.${i}.external_lot_code`}
              label={`Lot numarası ${i + 1}`}
            />
          </div>
          <div className="form-grid">
            <Field
              name={`lines.${i}.quantity`}
              label={`Miktar ${i + 1}`}
              type="decimal"
              hint={data.products.find(p => p.id === lines[i]?.product_id)?.base_unit ? "Stok birimi: " + units[data.products.find(p => p.id === lines[i]?.product_id)!.base_unit] : "Birim ürün kartından gelir; önce ürün seçin."}
            />
            <Field
              name={`lines.${i}.total_cost`}
              label={`Toplam maliyet ${i + 1} (EUR)`}
              type="decimal"
              hint="Birim fiyat değil, satırın toplam alış tutarı."
            />
          </div>
          <div className="form-grid">
            <Field
              name={`lines.${i}.expires_at`}
              label={`Son tüketim tarihi ${i + 1}`}
              type="date"
            />
          </div>
        </div>
      ))}
      <button
        type="button"
        className="button"
        disabled={fields.length >= 100}
        onClick={() => append({ ...blankLine })}
      >
        <Plus size={16} />
        Alış satırı ekle
      </button>
      <p className="hint">
        Miktar ve tutarda virgül veya nokta kullanabilirsiniz. Satır toplamları
        ve stok etkisi backend tarafından kaydedilir.
      </p>
    </>
  );
}
export function Receipts() {
  const data = useCatalog(),
    receipts = useRecords<Receipt>("/receipts"),
    [selected, setSelected] = useState(""),
    [created, setCreated] = useState("");
  const detail = useQuery({
    queryKey: ["receipt", selected],
    queryFn: () => request<ReceiptDetail>("/receipts/" + selected),
    enabled: !!selected,
    retry: false,
  });
  return (
    <State
      loading={data.loading || receipts.isPending}
      error={data.error || receipts.error}
    >
      <div className="stack">
        <Section id="create-record"
          title="Alış ve lot girişi"
          subtitle="Bir alıştaki her satır için ayrı lot ve stok girişi oluşturulur."
        >
          {created && (
            <Success>
              Alış kaydedildi. Lotlar ve stok hareketleri oluşturuldu.
            </Success>
          )}
          <CommandForm<z.infer<typeof receiptSchema>>
            schema={receiptSchema}
            defaults={{
              supplier_id: "",
              location_id: "",
              reference: "",
              lines: [{ ...blankLine }],
            }}
            path="/receipts"
            label="Alışı kaydet"
            confirmText="Alış, lotlar ve stok girişleri birlikte kaydedilecek. Lot numaraları, miktarlar ve toplam maliyetleri kontrol edin."
            payload={receiptPayload}
            onSuccess={(r) => {
              setSelected((r as ReceiptDetail).id);
              setCreated((r as ReceiptDetail).id);
            }}
          >
            <ReceiptFields data={data} />
          </CommandForm>
        </Section>
        <Section
          title="Alış kayıtları"
          subtitle="Satır ve lot ayrıntıları için kaydı açın."
        >
          <Table readonlyReason="Kesin kayıt korunur. Düzeltme yalnız desteklenen iade, iptal veya yeni işlemle yapılır."
            headers={["Referans", "Tedarikçi", "Depo", "Tarih", "İşlemler"]}
            empty={!receipts.data?.length}
            emptyMessage="Henüz alış yok. Üstte tedarikçi, depo ve lot satırlarını seçerek ilk alışı kaydedin."
          >
            {receipts.data?.map((x) => (
              <tr key={x.id}>
                <td className="code">{x.reference || x.id.slice(0, 8)}</td>
                <td>
                  {data.parties.find((p) => p.id === x.supplier_id)?.name ||
                    "—"}
                </td>
                <td>
                  {data.locations.find((l) => l.id === x.location_id)?.name ||
                    "—"}
                </td>
                <td>{dateTime(x.received_at)}</td>
                <td>
                  <button
                    id={"receipt-view-" + x.id}
                    className="text-button"
                    onClick={event => { event.currentTarget.focus(); setSelected(x.id); }}
                  >
                    Görüntüle
                  </button>
                </td>
              </tr>
            ))}
          </Table>
        </Section>
        {selected && <DetailDrawer title="Alış ayrıntıları" onClose={() => setSelected("")}>
          <State loading={detail.isPending} error={detail.error}>
            {detail.data && <>
              <dl className="record-facts">
                <div><dt>Referans numarası</dt><dd>{detail.data.reference || "Referans girilmedi"}</dd></div>
                <div><dt>Tedarikçi</dt><dd>{detail.data.supplier_name || data.parties.find(p => p.id === detail.data.supplier_id)?.name || detail.data.supplier_id}</dd></div>
                <div><dt>Kabul deposu</dt><dd>{detail.data.location_name || data.locations.find(l => l.id === detail.data.location_id)?.name || detail.data.location_id}</dd></div>
                <div><dt>Alış tarihi</dt><dd>{dateTime(detail.data.received_at)}</dd></div>
                {detail.data.total_cost != null && <div><dt>Gerçek toplam maliyet</dt><dd>{eur(detail.data.total_cost)}</dd></div>}
              </dl>
              <Table readonlyReason="Kesin kayıt korunur. Düzeltme yalnız desteklenen iade, iptal veya yeni işlemle yapılır." headers={["Ürün", "Lot", "Miktar", "Gerçek toplam maliyet"]} empty={!detail.data.lines.length}>
                {detail.data.lines.map(line => <tr key={line.id}>
                  <td>{line.product_name || data.products.find(p => p.id === line.product_id)?.name || line.product_id}</td>
                  <td className="code">{line.lot_code || data.lots.find(l => l.id === line.lot_id)?.external_code || line.lot_id}</td>
                  <td>{amount(line.quantity)} {units[line.unit || data.products.find(p => p.id === line.product_id)?.base_unit || "kg"]}</td>
                  <td>{eur(line.total_cost)}</td>
                </tr>)}
              </Table>
              <p className="caption">Kesin alış ve stok hareketleri değiştirilemez. Bu görünüm yalnız kaydı okur.</p>
              <RecordId id={detail.data.id} label="Alış kayıt kimliği"/>
            </>}
          </State>
        </DetailDrawer>}
      </div>
    </State>
  );
}
