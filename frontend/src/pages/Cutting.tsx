import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useFieldArray, useFormContext } from "react-hook-form";
import type { z } from "zod";
import { Plus, Scissors, Trash2 } from "lucide-react";
import { RecordActions } from "../components/record-actions";
import { DetailDrawer } from "../components/dialogs";
import { PartProductDialog } from "../components/catalog-product";
import { CommandForm, Field, Options, ArrayError } from "../components/forms";
import { Badge, Section, State, Table } from "../components/ui";
import {
  ModuleIntro,
  LotSelector,
  NumberInput,
  ProcessSteps,
  RecordId,
  ReviewSummary,
  StatusBadge,
  LotLink,
  StatCard,
} from "../components/workflow";
import { request } from "../lib/api";
import { useCatalog, useRecords } from "../lib/data";
import { amount, dateTime, eur } from "../lib/format";
import type { Stock, Operation } from "../lib/types";
import type { Recipe, Cutting } from "../lib/modules";
import {
  recipeSchema,
  cuttingDraftSchema,
  cuttingCloseSchema,
} from "../lib/module-validation";
import {
  recipePayload,
  cuttingDraftPayload,
  cuttingPostPayload,
} from "../lib/module-payloads";
import { balance } from "../lib/quantity";

type Catalog = ReturnType<typeof useCatalog>;
function RecipeFields({ data, onCreateProduct }: { data: Catalog; onCreateProduct: () => void }) {
  const { control, watch } = useFormContext<z.infer<typeof recipeSchema>>();
  const { fields, append, remove } = useFieldArray({ control, name: "lines" });
  const method = watch("allocation_method");
  const selectedLines = watch("lines");
  const parts = data.products.filter(p => p.type !== "raw" && p.base_unit === "kg");
  const sources = data.products.filter(p => p.type === "raw" && p.base_unit === "kg");
  return (
    <>
      <div className="form-grid cols-3">
        <Field name="code" label="Reçete kodu" />
        <Field name="version" label="Reçete sürümü" />
        <Field name="species" label="Hayvan türü" />
        <Field name="input_product_id" label="Kaynak kuzu ürünü">
          <Options
            items={data.products.filter(
              (p) => p.type === "raw" && p.base_unit === "kg",
            )}
          />
        </Field>
        <Field name="allocation_method" label="Maliyet dağıtım yöntemi">
          <option value="quantity">Miktar ağırlıklı (quantity)</option>
          <option value="value">Değer ağırlıklı (value)</option>
        </Field>
      </div>
      {!sources.length && <div className="notice"><p>Kaynak ürün bulunamadı. Hammadde türünde, kg birimli bütün kuzu ürünü gerekir. <Link to="/urunler">Ürün kataloğunu aç</Link></p></div>}
      <div className="selection-help">
        {!parts.length && <div role="status"><strong>Uygun parça ürünü bulunamadı</strong><p>Mamul veya Yan ürün türünde, stok birimi kg olan gerçek ürün kartları gerekir.</p></div>}
        <button type="button" className="button" onClick={onCreateProduct}><Plus size={16}/>Parça ürünü oluştur</button>
      </div>
      <p className="caption">
        Referans EUR/kg dağıtım anahtarıdır; satış fiyatı değildir. Yeni sürüm
        geçmiş maliyeti değiştirmez.
      </p>
      {fields.map((f, i) => (
        <div className="line-card" key={f.id}>
          <div className="line-title">
            <h4>Reçete parçası {i + 1}</h4>
            <button
              className="icon-button"
              type="button"
              aria-label={`Reçete parçası ${i + 1} sil`}
              disabled={fields.length === 1}
              onClick={() => remove(i)}
            >
              <Trash2 size={17} />
            </button>
          </div>
          <div className="form-grid">
            <Field
              name={`lines.${i}.product_id`}
              label={`Parça ürünü ${i + 1}`}
            >
              <option value="">Parça ürünü seçin</option>
              {parts.map(p => <option key={p.id} value={p.id} disabled={selectedLines.some((line, index) => index !== i && line.product_id === p.id)}>{p.name} · {p.sku} (kg)</option>)}
            </Field>
            <NumberInput
              name={`lines.${i}.reference_eur_per_kg`}
              label={`Referans EUR/kg ${i + 1}`}
              hint={
                method === "value"
                  ? "Değer yönteminde pozitif referans zorunlu."
                  : "İsteğe bağlı; satış fiyatı değildir."
              }
            />
          </div>
        </div>
      ))}
      <ArrayError name="lines" />
      <button
        className="button"
        type="button"
        onClick={() => append({ product_id: "", reference_eur_per_kg: "" })}
      >
        <Plus size={16} />
        Reçete parçası ekle
      </button>
    </>
  );
}
export function Cuttings() {
  const data = useCatalog(),
    recipes = useRecords<Recipe>("/recipes"),
    cuttings = useRecords<Operation>("/cuttings"),
    navigate = useNavigate();
  const [viewRecipe, setViewRecipe] = useState<Recipe | null>(null);
  const [creatingProduct, setCreatingProduct] = useState(false);
  const [showRecipe, setShowRecipe] = useState(false),
    [availability, setAvailability] = useState<Recipe | null>(null);
  return (
    <State
      loading={data.loading || recipes.isPending || cuttings.isPending}
      error={data.error || recipes.error || cuttings.error}
    >
      <div className="stack">
        <ModuleIntro
          title="Bir kaynaktan, izlenebilir parçalara."
          description="Reçeteyi seçin, fiilî ağırlıkları kaydedin. Lotlar ve gerçek maliyet dağıtımı backend onayıyla oluşur."
          icon={<Scissors size={24} />}
        />
        <ProcessSteps
          steps={[
            "Reçete sürümü",
            "Kesim taslağı",
            "Tartım ve onay",
            "Lot ve maliyet",
          ]}
          current={0}
        />
        <Section
          title="Kesim kayıtları"
          subtitle="Miktar ve değer karşılaştırması ayrı kaynak lotlar gerektirir; aynı kuzuyu iki kez tüketmeyin."
        >
          <Table readonlyReason="Kesin kayıt korunur. Düzeltme yalnız desteklenen iade, iptal veya yeni işlemle yapılır."
            headers={["Kesim", "Durum", "Dağıtım", "Gerçek maliyet", "Ayrıntı"]}
            empty={!cuttings.data?.length}
          >
            {cuttings.data?.map((c) => (
              <tr key={c.id}>
                <td className="code">{c.code}</td>
                <td>
                  <StatusBadge status={c.status} />
                </td>
                <td>
                  {c.allocation_method === "value"
                    ? "Değer ağırlıklı"
                    : "Miktar ağırlıklı"}
                </td>
                <td>
                  {c.status === "posted"
                    ? eur(c.total_cost)
                    : "Kapanış bekleniyor"}
                </td>
                <td>
                  <Link className="text-button" to={"/parcalama/" + c.id}>
                    Kesimi aç
                  </Link>
                </td>
              </tr>
            ))}
          </Table>
        </Section>
        <div className="split-grid">
          <Section
            title="Kesim taslağı oluştur"
            subtitle="Taslak stok tüketmez."
          >
            <CommandForm
              schema={cuttingDraftSchema}
              defaults={{ code: "", recipe_version_id: "" }}
              path="/cuttings"
              label="Kesim taslağı oluştur"
              confirmText="Seçili reçete sürümüyle değişmez konfigürasyonlu bir taslak açılacak."
              payload={cuttingDraftPayload}
              onSuccess={(r) => navigate("/parcalama/" + (r as Operation).id)}
              summary={(b) => (
                <ReviewSummary
                  items={[
                    ["Kesim", (b as { code: string }).code],
                    [
                      "Reçete",
                      recipes.data?.find(
                        (r) =>
                          r.id ===
                          (b as { recipe_version_id: string })
                            .recipe_version_id,
                      )?.code,
                    ],
                  ]}
                />
              )}
            >
              <div className="form-grid">
                <Field name="code" label="Kesim numarası" />
                <Field name="recipe_version_id" label="Kesim reçetesi">
                  <Options
                    items={(recipes.data || [])
                      .filter((r) => r.available)
                      .map((r) => ({
                        id: r.id,
                        name: `${r.code} · v${r.version} · ${r.allocation_method === "value" ? "Değer" : "Miktar"}`,
                      }))}
                  />
                </Field>
              </div>
            </CommandForm>
          </Section>
          <Section
            title="Reçete kitaplığı"
            subtitle="Sürümlü kaynak, parça ve dağıtım tanımları"
            action={
              <button
                className="button"
                onClick={() => setShowRecipe(!showRecipe)}
              >
                {showRecipe ? "Formu kapat" : "Yeni reçete"}
              </button>
            }
          >
            <div className="record-list">
              {recipes.data?.map((r) => (
                <article className="record-card" key={r.id}>
                  <div>
                    <strong>
                      {r.code} · v{r.version}
                    </strong>
                    <p>
                      {r.species} · {r.lines.length} parça ·{" "}
                      {r.allocation_method === "value" ? "Değer" : "Miktar"}{" "}
                      ağırlıklı
                    </p>
                    <Badge tone={r.available ? "green" : "amber"}>
                      {r.available ? "Kullanıma açık" : "Kullanıma kapalı"}
                    </Badge>
                  </div>
                  <RecordActions onView={() => setViewRecipe(r)} readonlyReason="Sürüm geçmişi korunur; tanım değişikliği için yeni reçete sürümü oluşturun."><button className="button" onClick={() => setAvailability(r)}>Kullanılabilirlik</button></RecordActions>
                </article>
              ))}
            </div>
            {availability && (
              <div className="form-area">
                <CommandForm
                  key={availability.id}
                  schema={cuttingDraftSchema.pick({ code: true })}
                  defaults={{ code: availability.code }}
                  path={`/recipes/${availability.id}/availability`}
                  label={
                    availability.available
                      ? "Sürümü kullanıma kapat"
                      : "Sürümü kullanıma aç"
                  }
                  confirmText="Bu karar geçmiş kayıtları yeniden fiyatlamaz. Kapalı sürümle yeni kesim/kapanış yapılamaz."
                  payload={() => ({ available: !availability.available })}
                  onSuccess={() => setAvailability(null)}
                >
                  <p>
                    {availability.code} · v{availability.version}
                  </p>
                </CommandForm>
              </div>
            )}
          </Section>
        </div>
        {showRecipe && (
          <Section title="Reçete oluştur">
            <CommandForm
              schema={recipeSchema}
              defaults={{
                code: "",
                version: "1",
                species: "Kuzu",
                input_product_id: "",
                allocation_method: "quantity",
                lines: [{ product_id: "", reference_eur_per_kg: "" }],
              }}
              path="/recipes"
              label="Reçeteyi kaydet"
              confirmText="Yeni reçete sürümü kaydedilecek. Fiilî parça ağırlıkları kesim sırasında girilir."
              payload={recipePayload}
              onSuccess={() => setShowRecipe(false)}
            >
              <RecipeFields data={data} onCreateProduct={() => setCreatingProduct(true)} />
            </CommandForm>
          </Section>
        )}
        {viewRecipe && <DetailDrawer title="Reçete ayrıntıları" onClose={() => setViewRecipe(null)}><dl className="record-facts"><div><dt>Reçete / sürüm</dt><dd>{viewRecipe.code} · v{viewRecipe.version}</dd></div><div><dt>Kaynak ürün</dt><dd>{data.products.find(p => p.id === viewRecipe.input_product_id)?.name || viewRecipe.input_product_id}</dd></div><div><dt>Hayvan türü</dt><dd>{viewRecipe.species}</dd></div><div><dt>Dağıtım</dt><dd>{viewRecipe.allocation_method === "value" ? "Değer ağırlıklı" : "Miktar ağırlıklı"}</dd></div></dl><Table headers={["Parça ürünü","Referans EUR/kg"]}>{viewRecipe.lines.map(line=><tr key={line.product_id}><td>{data.products.find(p=>p.id===line.product_id)?.name || line.product_id}</td><td>{line.reference_eur_per_kg ? eur(line.reference_eur_per_kg) : "Tanımlanmadı"}</td></tr>)}</Table><RecordId id={viewRecipe.id}/></DetailDrawer>}
        {creatingProduct && <PartProductDialog onClose={() => setCreatingProduct(false)} />}
      </div>
    </State>
  );
}
function ClosingFields({
  data,
  stocks,
  cutting,
}: {
  data: Catalog;
  stocks: Stock[];
  cutting: Cutting;
}) {
  const { control, watch } =
    useFormContext<z.infer<typeof cuttingCloseSchema>>();
  const outputs = useFieldArray({ control, name: "outputs" }),
    differences = useFieldArray({ control, name: "differences" });
  const v = watch();
  const b = balance(
    v.quantity || "",
    v.outputs?.map((x) => x.quantity || "") || [],
    v.differences?.map((x) => x.quantity || "") || [],
  );
  return (
    <>
      <div className="form-grid">
        <LotSelector
          name="source"
          label="Kaynak kuzu lotu / konum"
          stocks={stocks}
          {...data}
          productId={cutting.allocation_snapshot.input_product_id}
        />
        <NumberInput name="quantity" label="Kesime alınan kg" />
        <Field name="output_location_id" label="Parça kabul deposu">
          <Options
            items={data.locations.filter((l) => l.kind === "warehouse")}
          />
        </Field>
      </div>
      <h3>Fiilî parça ağırlıkları</h3>
      {outputs.fields.map((f, i) => (
        <div className="line-card" key={f.id}>
          <div className="line-title">
            <h4>
              {data.products.find((p) => p.id === f.product_id)?.name ||
                "Parça"}{" "}
              {f.byproduct && <Badge tone="amber">Yan ürün · stoklanır</Badge>}
            </h4>
            <button
              type="button"
              className="icon-button"
              disabled={outputs.fields.length === 1}
              aria-label={`Çıktı ${i + 1} sil`}
              onClick={() => outputs.remove(i)}
            >
              <Trash2 size={17} />
            </button>
          </div>
          <div className="form-grid">
            <NumberInput
              name={`outputs.${i}.quantity`}
              label={`Parça kg ${i + 1}`}
            />
            <Field
              name={`outputs.${i}.lot_code`}
              label={`Parça lot kodu ${i + 1}`}
            />
            <Field
              name={`outputs.${i}.expires_at`}
              label={`Parça SKT ${i + 1}`}
              type="date"
            />
            <Field
              name={`outputs.${i}.explanation`}
              label={`Parça açıklaması ${i + 1}`}
              hint={
                f.byproduct
                  ? "Yan ürün miktarı ve nedeni zorunludur."
                  : "İsteğe bağlı."
              }
            />
          </div>
        </div>
      ))}
      <p className="caption">
        Sıfır ölçülen parçayı satırdan çıkarın. Yan ürün, fire satırı olarak
        kaybolmaz; ayrı lot ve stok oluşturur.
      </p>
      <ArrayError name="outputs" />
      <h3>Açıklanmış farklar</h3>
      {differences.fields.map((f, i) => (
        <div className="line-card" key={f.id}>
          <div className="line-title">
            <h4>Fark {i + 1}</h4>
            <button
              className="icon-button"
              type="button"
              aria-label={`Fark ${i + 1} sil`}
              onClick={() => differences.remove(i)}
            >
              <Trash2 size={17} />
            </button>
          </div>
          <div className="form-grid cols-3">
            <Field name={`differences.${i}.kind`} label={`Fark türü ${i + 1}`}>
              <option value="waste">Fire</option>
              <option value="other_loss">Diğer açıklanmış kayıp</option>
            </Field>
            <NumberInput
              name={`differences.${i}.quantity`}
              label={`Fark kg ${i + 1}`}
            />
            <Field
              name={`differences.${i}.reason`}
              label={`Fark nedeni ${i + 1}`}
            />
          </div>
        </div>
      ))}
      <button
        className="button"
        type="button"
        onClick={() =>
          differences.append({ kind: "waste", quantity: "", reason: "" })
        }
      >
        <Plus size={16} />
        Açıklanmış fark ekle
      </button>
      <div
        className={"mass-balance " + (b?.balanced ? "balanced" : "")}
        role="status"
      >
        <strong>Ağırlık dengesi</strong>
        <p>
          {b
            ? `${amount(b.input)} kg giriş = ${amount(b.output)} kg ürün/yan ürün + ${amount(b.difference)} kg açıklanmış fark`
            : "Tüm tartım alanlarını tamamlayın."}
        </p>
        {b && !b.balanced && <span>Denge sağlanmadı; kayıt gönderilmez.</span>}
      </div>
    </>
  );
}
export function CuttingPage() {
  const { id = "" } = useParams();
  const data = useCatalog(),
    stocks = useRecords<Stock>("/stocks"),
    query = useQuery({
      queryKey: ["cutting", id],
      queryFn: () => request<Cutting>("/cuttings/" + id),
      retry: false,
    });
  const c = query.data;
  const mass =
    c?.status === "posted"
      ? balance(
          c.inputs[0]?.quantity || "",
          c.outputs.map((o) => o.quantity),
          [c.loss_quantity],
        )
      : null;
  return (
    <State
      loading={data.loading || stocks.isPending || query.isPending}
      error={data.error || stocks.error || query.error}
    >
      {c && (
        <div className="stack">
          <div className="detail-heading">
            <div>
              <Link className="text-button" to="/parcalama">
                ← Kesim kayıtları
              </Link>
              <h2>{c.code}</h2>
              <p>
                {c.allocation_snapshot.code} · v{c.allocation_snapshot.version}{" "}
                · {c.allocation_method === "value" ? "Değer" : "Miktar"}{" "}
                ağırlıklı
              </p>
            </div>
            <StatusBadge status={c.status} />
          </div>
          <RecordId id={c.id} label="Kesim UUID" />
          <ProcessSteps
            steps={[
              "Reçete sürümü",
              "Kesim taslağı",
              "Tartım ve onay",
              "Lot ve maliyet",
            ]}
            current={c.status === "posted" ? 3 : 2}
          />
          {c.status === "posted" ? (
            <>
              {mass && (
                <div
                  className="weight-balance"
                  aria-label="Kayıtlı ağırlık dengesi"
                >
                  <div>
                    <small>Başlangıç ağırlığı</small>
                    <strong>{amount(mass.input)} kg</strong>
                  </div>
                  <b>=</b>
                  <div>
                    <small>Toplam parça ağırlığı</small>
                    <strong>{amount(mass.output)} kg</strong>
                  </div>
                  <b>+</b>
                  <div>
                    <small>Açıklanan fark</small>
                    <strong>{amount(c.loss_quantity)} kg</strong>
                  </div>
                </div>
              )}
              <div className="stat-grid">
                <StatCard
                  label="Gerçek toplam maliyet"
                  value={eur(c.total_cost)}
                  note="Backend kesin kaydı"
                />
                <StatCard
                  label="Maliyet dağıtımı"
                  value={
                    c.allocation_method === "value"
                      ? "Değere göre"
                      : "Miktara göre"
                  }
                  note="Kayıt anındaki reçete"
                />
                <StatCard
                  label="Açıklanmış fark"
                  value={amount(c.loss_quantity) + " kg"}
                />
                <StatCard
                  label="Kapanış"
                  value={c.posted_at ? dateTime(c.posted_at) : "—"}
                />
              </div>
              <Section
                title="Parça lotları ve maliyetler"
                subtitle="Fiilî ölçüler ve kesin backend dağıtımı. Referans değer satış fiyatı değildir."
              >
                <Table readonlyReason="Kesin kayıt korunur. Düzeltme yalnız desteklenen iade, iptal veya yeni işlemle yapılır."
                  headers={[
                    "Ürün / lot",
                    "Fiilî kg",
                    "Dağıtılan maliyet",
                    "EKP EUR/kg",
                    "Referans EUR/kg",
                  ]}
                  empty={!c.outputs.length}
                >
                  {c.outputs.map((o) => {
                    const lot = data.lots.find((l) => l.id === o.lot_id),
                      product = data.products.find(
                        (p) => p.id === lot?.product_id,
                      );
                    return (
                      <tr key={o.id}>
                        <td>
                          <strong>{product?.name}</strong>
                          <LotLink id={o.lot_id} code={lot?.external_code} />
                        </td>
                        <td>{amount(o.quantity)} kg</td>
                        <td>{eur(o.allocated_cost)}</td>
                        <td>{eur(o.unit_cost_display)}</td>
                        <td>{eur(o.reference_eur_per_kg ?? undefined)}</td>
                      </tr>
                    );
                  })}
                </Table>
              </Section>
              <Section title="Kaynak lot bağlantıları">
                <Table readonlyReason="Kesin kayıt korunur. Düzeltme yalnız desteklenen iade, iptal veya yeni işlemle yapılır."
                  headers={["Kaynak lot", "Parça lotu", "Atfedilen giriş kg"]}
                >
                  {c.lot_links.map((l) => (
                    <tr key={l.id}>
                      <td>
                        <LotLink
                          id={l.input_lot_id}
                          code={
                            data.lots.find((x) => x.id === l.input_lot_id)
                              ?.external_code
                          }
                        />
                      </td>
                      <td>
                        <LotLink
                          id={l.output_lot_id}
                          code={
                            data.lots.find((x) => x.id === l.output_lot_id)
                              ?.external_code
                          }
                        />
                      </td>
                      <td>{amount(l.attributed_input_quantity)} kg</td>
                    </tr>
                  ))}
                </Table>
                {c.differences.map((d) => (
                  <p key={d.id} className="caption">
                    {d.kind === "waste" ? "Fire" : "Diğer kayıp"}:{" "}
                    {amount(d.quantity)} kg · {d.reason}
                  </p>
                ))}
              </Section>
            </>
          ) : (
            <Section
              title="Kesim tartımı ve kapanış"
              subtitle="Parça ölçüleri, yan ürünler ve farklar tek transaction ile kaydedilir."
            >
              <CommandForm
                key={c.id}
                schema={cuttingCloseSchema}
                defaults={{
                  source: "",
                  quantity: "",
                  output_location_id: "",
                  outputs: c.allocation_snapshot.lines.map((l) => ({
                    product_id: l.product_id,
                    quantity: "",
                    lot_code: "",
                    expires_at: "",
                    explanation: "",
                    byproduct: l.product?.type === "byproduct",
                  })),
                  differences: [],
                }}
                path={`/cuttings/${c.id}/post`}
                label="Kesimi kapat"
                confirmText="Fiilî tüketim stoktan düşecek; parça lotları, gerçek maliyetler ve izlenebilirlik kayıtları kesinleşecek."
                payload={cuttingPostPayload}
                summary={(body) => {
                  const b = body as ReturnType<typeof cuttingPostPayload>;
                  return (
                    <ReviewSummary
                      items={[
                        [
                          "Kesime alınan",
                          amount(String(b.consumed_inputs[0].quantity)) + " kg",
                        ],
                        ["Çıktı lotları", b.outputs.length],
                        [
                          "Dağıtım yöntemi",
                          c.allocation_method === "value"
                            ? "Değer ağırlıklı"
                            : "Miktar ağırlıklı",
                        ],
                      ]}
                    />
                  );
                }}
              >
                <ClosingFields
                  data={data}
                  stocks={stocks.data || []}
                  cutting={c}
                />
              </CommandForm>
            </Section>
          )}
        </div>
      )}
    </State>
  );
}
