import { useState } from "react";
import { useFormContext } from "react-hook-form";
import type { z } from "zod";
import { Plus } from "lucide-react";
import { productPayload, partyPayload, locationPayload } from "../lib/payloads";
import { useCatalog } from "../lib/data";
import {
  amount,
  locationKinds,
  productTypes,
  roles,
  units,
} from "../lib/format";
import {
  productSchema,
  partySchema,
  locationSchema,
  cleanDecimal,
} from "../lib/validation";
import { CommandForm, Field, Options } from "../components/forms";
import { Badge, Section, State, Table } from "../components/ui";

function ProductFields() {
  const { watch } = useFormContext();
  return (
    <div className="form-grid">
      <Field name="sku" label="SKU" />
      <Field name="name" label="Ürün adı" />
      <Field name="type" label="Ürün türü">
        {Object.entries(productTypes).map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </Field>
      <Field name="base_unit" label="Stok birimi">
        {Object.entries(units).map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </Field>
      {watch("base_unit") === "package" && (
        <Field
          name="package_weight_kg"
          label="Bir paket kaç kg?"
          type="decimal"
          hint="Örneğin: 1 veya 0,5"
        />
      )}
    </div>
  );
}
export function Products() {
  const data = useCatalog(),
    [search, setSearch] = useState(""),
    [type, setType] = useState(""),
    [adding, setAdding] = useState(false);
  const products = data.products.filter(
    (x) =>
      (!type || x.type === type) &&
      (x.name + " " + x.sku)
        .toLocaleLowerCase("tr")
        .includes(search.toLocaleLowerCase("tr")),
  );
  return (
    <State loading={data.loading} error={data.error}>
      <Section
        title="Ürün kataloğu"
        subtitle="Hammadde, mamul ve yan ürün kartları"
        action={
          <button className="button primary" onClick={() => setAdding(!adding)}>
            <Plus size={17} />
            Ürün ekle
          </button>
        }
      >
        {adding && (
          <div className="form-area">
            <h3>Yeni ürün</h3>
            <CommandForm<z.infer<typeof productSchema>>
              schema={productSchema}
              defaults={{
                sku: "",
                name: "",
                type: "raw",
                base_unit: "kg",
                package_weight_kg: "",
              }}
              path="/products"
              label="Ürünü oluştur"
              confirmText="Yeni ürün kartı oluşturulacak. Birim ve paket dönüşümü bu sürümde sonradan değiştirilemez."
              payload={productPayload}
            >
              <ProductFields />
            </CommandForm>
          </div>
        )}
        <div className="filters">
          <label>
            Ürün ara
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="SKU veya ürün adı"
            />
          </label>
          <label>
            Tür
            <select value={type} onChange={(e) => setType(e.target.value)}>
              <option value="">Tüm türler</option>
              {Object.entries(productTypes).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
        </div>
        <Table
          headers={["SKU", "Ürün", "Tür", "Stok birimi", "Paket dönüşümü"]}
          empty={!products.length}
        >
          {products.map((x) => (
            <tr key={x.id}>
              <td>
                <span className="code">{x.sku}</span>
              </td>
              <td className="strong">{x.name}</td>
              <td>
                <Badge>{productTypes[x.type]}</Badge>
              </td>
              <td>{units[x.base_unit]}</td>
              <td>
                {x.package_weight_kg
                  ? amount(x.package_weight_kg) + " kg / paket"
                  : "—"}
              </td>
            </tr>
          ))}
        </Table>
        <p className="table-foot">
          {products.length} kayıt • Arama tüm yüklenen API sayfalarında
          uygulanır.
        </p>
      </Section>
    </State>
  );
}
function PartyFields() {
  const {
    register,
    formState: { errors },
  } = useFormContext();
  return (
    <>
      <div className="form-grid">
        <Field name="name" label="Firma adı" />
        <Field name="contact" label="İletişim bilgisi" />
      </div>
      <div className="role-group">
        <span>Firma rolleri</span>
        {Object.entries(roles).map(([v, l]) => (
          <label key={v}>
            <input type="checkbox" value={v} {...register("roles")} />
            {l}
          </label>
        ))}
        {errors.roles && (
          <small className="field-error">En az bir rol seçin.</small>
        )}
      </div>
    </>
  );
}
export function Parties() {
  const data = useCatalog();
  return (
    <State loading={data.loading} error={data.error}>
      <div className="stack">
        <Section
          title="İş ortakları"
          subtitle="Tedarikçi ve dış üreticiler tek bir firma kartında tutulur."
        >
          <Table
            headers={["Firma", "Roller", "İletişim"]}
            empty={!data.parties.length}
          >
            {data.parties.map((x) => (
              <tr key={x.id}>
                <td className="strong">{x.name}</td>
                <td>
                  <div className="badges">
                    {x.roles.map((r) => (
                      <Badge key={r}>{roles[r]}</Badge>
                    ))}
                  </div>
                </td>
                <td>{x.contact || "—"}</td>
              </tr>
            ))}
          </Table>
        </Section>
        <Section title="Firma oluştur">
          <CommandForm<z.infer<typeof partySchema>>
            schema={partySchema}
            defaults={{ name: "", roles: ["supplier"], contact: "" }}
            path="/parties"
            label="Firmayı oluştur"
            confirmText="Firma seçilen rollerle kaydedilecek."
            payload={partyPayload}
          >
            <PartyFields />
          </CommandForm>
        </Section>
      </div>
    </State>
  );
}
function LocationFields({ data }: { data: ReturnType<typeof useCatalog> }) {
  const { watch } = useFormContext();
  return (
    <div className="form-grid">
      <Field name="name" label="Depo / konum adı" />
      <Field name="kind" label="Konum türü">
        {Object.entries(locationKinds).map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </Field>
      {watch("kind") === "external_producer" && (
        <Field name="party_id" label="İlgili dış üretici">
          <Options
            items={data.parties.filter((p) => p.roles.includes("producer"))}
          />
        </Field>
      )}
    </div>
  );
}
export function Locations() {
  const data = useCatalog();
  return (
    <State loading={data.loading} error={data.error}>
      <div className="stack">
        <Section
          title="Depolar ve üretici konumları"
          subtitle="Karantina stoğu kullanılabilir stok sayılmaz."
        >
          <Table
            headers={["Konum", "Tür", "Dış üretici"]}
            empty={!data.locations.length}
          >
            {data.locations.map((x) => (
              <tr key={x.id}>
                <td className="strong">{x.name}</td>
                <td>
                  <Badge tone={x.kind === "quarantine" ? "amber" : ""}>
                    {locationKinds[x.kind]}
                  </Badge>
                </td>
                <td>
                  {data.parties.find((p) => p.id === x.party_id)?.name || "—"}
                </td>
              </tr>
            ))}
          </Table>
        </Section>
        <Section title="Konum oluştur">
          <CommandForm<z.infer<typeof locationSchema>>
            schema={locationSchema}
            defaults={{ name: "", kind: "warehouse", party_id: "" }}
            path="/locations"
            label="Konumu oluştur"
            confirmText="Yeni stok konumu oluşturulacak. Dış üretici konumu seçtiğiniz firmaya bağlanacak."
            payload={locationPayload}
          >
            <LocationFields data={data} />
          </CommandForm>
        </Section>
      </div>
    </State>
  );
}
