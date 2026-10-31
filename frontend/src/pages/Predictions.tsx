import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useFormContext } from "react-hook-form";
import { Sparkles, FlaskConical } from "lucide-react";
import { CommandForm, Field, Options, ArrayError } from "../components/forms";
import { Badge, Section, State, Table } from "../components/ui";
import {
  CriticalNotice,
  ModuleIntro,
  NumberInput,
  RecordId,
  StatCard,
} from "../components/workflow";
import { request } from "../lib/api";
import { useCatalog, useRecords } from "../lib/data";
import { dateTime } from "../lib/format";
import { displayDecimal, displayEuro, displayYield } from "../lib/presentation";
import type { Operation } from "../lib/types";
import {
  partNames,
  type ModelInfo,
  type Prediction,
  type Recipe,
  type Part,
} from "../lib/modules";
import {
  productionPredictionSchema,
  cuttingPredictionSchema,
} from "../lib/module-validation";
import {
  productionPredictionPayload,
  cuttingPredictionPayload,
} from "../lib/module-payloads";
import { readHistory, remember } from "../lib/history";
import type { z } from "zod";
import { modelHint, predictionSchemaForModel } from "../lib/prediction-domain";

const warning =
  "Bu model sentetik verilerle eğitilmiştir. Gerçek işletme verileriyle doğruluğu henüz kanıtlanmamıştır.";
export const predictionLabels: Record<string, { label: string; unit: string }> =
  {
    predicted_finished_quantity: { label: "Mamul miktarı", unit: "paket" },
    predicted_yield_ratio: { label: "Üretim verimi", unit: "kg/kg" },
    predicted_total_cost_eur: { label: "Toplam maliyet", unit: "EUR" },
    predicted_ekp_eur_per_unit: { label: "Birim EKP", unit: "EUR/paket" },
    predicted_total_weight_kg: { label: "Toplam parça ağırlığı", unit: "kg" },
    predicted_difference_kg: { label: "Açıklanması gereken fark", unit: "kg" },
    ...Object.fromEntries(
      Object.entries(partNames).map(([key, label]) => [
        "predicted_" + key + "_kg",
        { label, unit: "kg" },
      ]),
    ),
  };
function ProductionFields({
  data,
  operations,
  model,
}: {
  data: ReturnType<typeof useCatalog>;
  operations: Operation[];
  model: ModelInfo;
}) {
  const { watch, setValue } =
    useFormContext<z.infer<typeof productionPredictionSchema>>();
  const operation = watch("operation_id");
  return (
    <>
      <div className="actions">
        <button type="button" className="button" disabled={!model.example_inputs} onClick={() => {
          for (const [key, value] of Object.entries(model.example_inputs || {})) {
            setValue(key as keyof z.infer<typeof productionPredictionSchema>, value, { shouldValidate: true, shouldDirty: true });
          }
        }}>Geçerli üretim örneğini doldur</button>
        <span className="caption">Sayısal plan örneği; gerçek stok veya sonuç değildir.</span>
      </div>
      <fieldset className="form-section ai-input-card"><legend>Üretim planı</legend>      <div className="form-grid">
        <Field name="meat_type" label="Et türü">
          <option value="beef">Sığır</option>
          <option value="lamb">Kuzu</option>
        </Field>
        <Field name="planned_producer_profile" label="Sentetik üretici profili">
          <option value="producer_a">Kurgusal profil A</option>
          <option value="producer_b">Kurgusal profil B</option>
          <option value="producer_c">Kurgusal profil C</option>
        </Field>
      </div>
      </fieldset>
      <fieldset className="form-section ai-input-card"><legend>Malzeme miktarları</legend><div className="form-grid cols-3">        <NumberInput hint={modelHint(model, "meat_kg")} placeholder={model.example_inputs?.meat_kg} name="meat_kg" label="Planlanan et (kg)" />
        <NumberInput hint={modelHint(model, "spice_kg")} placeholder={model.example_inputs?.spice_kg} name="spice_kg" label="Planlanan baharat (kg)" />
        <NumberInput hint={modelHint(model, "casing_kg")} placeholder={model.example_inputs?.casing_kg} name="casing_kg" label="Planlanan kılıf (kg)" />
</div></fieldset>
      <fieldset className="form-section ai-input-card"><legend>Maliyetler · EUR</legend><div className="form-grid">        <NumberInput hint={modelHint(model, "meat_cost_eur")} placeholder={model.example_inputs?.meat_cost_eur} name="meat_cost_eur" label="Bilinen et maliyeti (EUR)" />
        <NumberInput
          name="spice_cost_eur"
          hint={modelHint(model, "spice_cost_eur")} placeholder={model.example_inputs?.spice_cost_eur}
          label="Bilinen baharat maliyeti (EUR)"
        />
        <NumberInput
          name="casing_cost_eur"
          hint={modelHint(model, "casing_cost_eur")} placeholder={model.example_inputs?.casing_cost_eur}
          label="Bilinen kılıf maliyeti (EUR)"
        />
        <NumberInput
          name="estimated_service_eur"
          label="Hizmet ön teklifi (EUR)"
          placeholder={model.example_inputs?.estimated_service_eur}
          hint={modelHint(model, "estimated_service_eur") + " İşlem öncesi bağımsız teklif; fiilî sonuç girilmez."}
        />
</div></fieldset>
      <fieldset className="form-section ai-input-card"><legend>Paket bilgileri</legend><div className="form-grid">        <NumberInput hint={modelHint(model, "package_weight_kg")} placeholder={model.example_inputs?.package_weight_kg} name="package_weight_kg" label="Paket ağırlığı (kg)" />
        <Field
          name="output_product_id"
          label="Tahminin paket ürünü"
          hint={
            operation
              ? "Bağlı işlem için zorunlu; paket ağırlığı kayıtlı ürünle eşleşir."
              : "İsteğe bağlı; referans girilmezse gerçekleşme eşleşmez."
          }
        >
          <Options
            items={data.products.filter(
              (p) => p.type === "finished" && p.base_unit === "package",
            )}
          />
        </Field>
</div></fieldset>
      <fieldset className="form-section ai-input-card"><legend>İsteğe bağlı işlem bağlantısı</legend><div className="form-grid">        <Field name="operation_id" label="Üretim operasyon referansı">
          <Options
            items={operations
              .filter(
                (o) => o.kind === "external_production" && o.status === "draft",
              )
              .map((o) => ({ id: o.id, name: o.code }))}
            placeholder="İlişkisiz tahmin (isteğe bağlı)"
          />
        </Field>
</div></fieldset>
      {!data.products.some(p => p.type === "finished" && p.base_unit === "package") && <p className="notice">İlişkisiz üretim tahmini için ürün gerekmez. İşlemle karşılaştırmak için <Link to="/urunler">Ürünler</Link> sayfasında paket ağırlığı tanımlı mamul oluşturun ve başlamamış üretim taslağını seçin.</p>}
      <p className="caption">Aralıklar seçili modelin metadata’sından gelir. Operasyon bağlantısı isteğe bağlıdır; başlamış işleme yeni tahmin kaydedilemez.</p>
    </>
  );
}
function CuttingFields({
  data,
  operations,
  recipes,
  model,
}: {
  data: ReturnType<typeof useCatalog>;
  operations: Operation[];
  recipes: Recipe[];
  model: ModelInfo;
}) {
  const { watch, setValue } =
      useFormContext<z.infer<typeof cuttingPredictionSchema>>(),
    recipeId = watch("recipe_version_id"),
    previous = useRef(recipeId);
  const recipe = useQuery({
    queryKey: ["recipe", recipeId],
    queryFn: () => request<Recipe>("/recipes/" + recipeId),
    enabled: !!recipeId,
    retry: false,
  });
  useEffect(() => {
    if (previous.current !== recipeId) {
      setValue("part_products", {
        leg: "",
        shoulder: "",
        back: "",
        rib: "",
        mince: "",
      });
      setValue("operation_id", "");
      previous.current = recipeId;
    }
  }, [recipeId, setValue]);
  const selected = recipe.data;
  const eligibleRecipes = recipes.filter(r => r.available && r.species === "Kuzu" && r.lines.length === 5 && r.lines.every(line => data.products.some(p => p.id === line.product_id && p.type === "finished" && p.base_unit === "kg")));
  return (
    <>
      <div className="actions">
        <button type="button" className="button" disabled={!model.example_inputs} onClick={() => {
          setValue("input_weight_kg", model.example_inputs?.input_weight_kg || "", { shouldValidate: true, shouldDirty: true });
        }}>Geçerli kesim örneğini doldur</button>
        <span className="caption">Sayısal örnek; reçeteyi ve beş gerçek ürün eşlemesini ayrıca seçin.</span>
      </div>
      {!eligibleRecipes.length && <p className="notice">Tahmin için kullanılabilir Kuzu reçetesi ve beş farklı kg mamul gerekir. <Link to="/parcalama">Parçalama sayfasında reçete oluşturun</Link>; parça ürünlerini <Link to="/urunler">Ürünler</Link> sayfasında tanımlayın.</p>}
      <fieldset className="form-section ai-input-card"><legend>Kuzu parçalama planı</legend>
      <div className="form-grid">
        <Field name="recipe_version_id" label="Tahmin reçete sürümü">
          <Options
            items={eligibleRecipes.map((r) => ({ id: r.id, name: r.code + " · v" + r.version }))}
          />
        </Field>
        <Field name="species" label="Tahmin hayvan türü">
          <option value="Kuzu">Kuzu</option>
        </Field>
        <NumberInput
          name="input_weight_kg"
          label="Tahmin giriş ağırlığı (kg)"
          hint={modelHint(model, "input_weight_kg")} placeholder={model.example_inputs?.input_weight_kg}
        />
        <Field name="operation_id" label="Kesim operasyon referansı">
          <Options
            items={operations
              .filter(
                (o) =>
                  o.kind === "cutting" &&
                  o.status === "draft" &&
                  o.recipe_version_id === recipeId,
              )
              .map((o) => ({ id: o.id, name: o.code }))}
            placeholder="İlişkisiz tahmin (isteğe bağlı)"
          />
        </Field>
      </div>
      </fieldset>
      {recipeId && (
        <State loading={recipe.isPending} error={recipe.error}>
          <h3>Reçete parçası → gerçek ürün eşlemesi</h3>
          <p className="caption">
            Her parça için reçeteden farklı bir ürün seçin. Eşleme kullanıcı
            konfigürasyonudur.
          </p>
          <div className="form-grid">
            {Object.entries(partNames).map(([key, label]) => (
              <Field
                key={key}
                name={"part_products." + key}
                label={label + " ürün eşlemesi"}
              >
                <Options
                  items={data.products.filter(
                    (p) =>
                      p.type === "finished" &&
                      p.base_unit === "kg" &&
                      selected?.lines.some((l) => l.product_id === p.id),
                  )}
                />
              </Field>
            ))}
          </div>
          <ArrayError name="part_products" />
        </State>
      )}
    </>
  );
}
function predictionValue(key: string, value: string | null) {
  if (value === null) return "—";
  if (key.includes("yield_ratio")) return displayYield(value);
  if (key.includes("cost") || key.includes("ekp")) return displayEuro(value);
  return displayDecimal(value) + " " + (predictionLabels[key]?.unit || "");
}
export function PredictionResult({
  prediction: p,
}: {
  prediction: Prediction;
}) {
  const fields =
    p.kind === "production"
      ? [
          "predicted_finished_quantity",
          "predicted_ekp_eur_per_unit",
          "predicted_total_cost_eur",
          "predicted_yield_ratio",
        ]
      : [
          "predicted_total_weight_kg",
          "predicted_yield_ratio",
          "predicted_difference_kg",
        ];
  return (
    <div className="prediction-main">
      <Section
        title={
          p.kind === "production"
            ? "Üretim tahmin sonucu"
            : "Kuzu parçalama tahmin sonucu"
        }
        subtitle={
          "Tahmin · " +
          dateTime(p.predicted_at) +
          " · Kesin stok veya maliyet kaydı oluşturmaz."
        }
      >
        <div className="stack">
          <div className="prediction-source">
            <Badge tone="amber">{p.data_origin}</Badge>
            <span>{warning}</span>
          </div>
          <p className="caption">Kayıtlı model sürümü: <code>{p.model_version}</code></p>
          <div className="stat-grid">
            {fields.map((k) => (
              <StatCard
                key={k}
                label={
                  k.includes("ekp")
                    ? "Tahmini EKP / paket"
                    : k.includes("yield_ratio")
                      ? p.kind === "production"
                        ? "Tahmini üretim verimi"
                        : "Tahmini kesim verimi"
                      : "Tahmini " +
                        predictionLabels[k].label.toLocaleLowerCase("tr")
                }
                value={predictionValue(k, p[k as keyof Prediction] as string)}
              />
            ))}
          </div>
          {p.kind === "cutting" && <div className="prediction-parts" aria-label="Tahmini parça ağırlıkları">
            {Object.entries(partNames).map(([key, name]) => <div key={key}><div><span>{"Tahmini "+name.toLocaleLowerCase("tr")}</span><strong>{predictionValue("predicted_" + key + "_kg", p[("predicted_" + key + "_kg") as keyof Prediction] as string)}</strong></div><progress aria-label={name+" tahmini ağırlık"} max={Number(p.predicted_total_weight_kg)} value={Number(p[("predicted_" + key + "_kg") as keyof Prediction])}/></div>)}
          </div>}
          {p.actual_unavailable_reason && (
            <p className="money-note">{p.actual_unavailable_reason}</p>
          )}
          <h3>Tahmin ve gerçekleşen</h3>
          <Table
            headers={[
              "Hedef / birim",
              "Tahmin",
              "Gerçekleşen",
              "Mutlak sapma",
              "Sapma %",
            ]}
            empty={!p.comparison}
          >
            {Object.entries(p.comparison || {}).map(([key, c]) => (
              <tr key={key}>
                <td>
                  <strong>{key === 'predicted_yield_ratio' && p.kind === 'cutting' ? 'Kesim verimi' : predictionLabels[key]?.label || key}</strong>
                  <small>
                    {key.includes("yield_ratio")
                      ? "Yüzde"
                      : predictionLabels[key]?.unit}
                  </small>
                </td>
                <td>{predictionValue(key, c.predicted)}</td>
                <td>
                  {c.actual === null
                    ? "Henüz gerçekleşmedi"
                    : predictionValue(key, c.actual)}
                </td>
                <td>
                  {key.includes("yield_ratio") && c.absolute_deviation !== null
                    ? displayYield(c.absolute_deviation).replace("%", " puan")
                    : predictionValue(key, c.absolute_deviation)}
                </td>
                <td>
                  {c.percentage_deviation === null
                    ? "—"
                    : displayDecimal(c.percentage_deviation, 2) + "%"}
                </td>
              </tr>
            ))}
          </Table>
          <p className="caption">
            Sapmalar kesin gerçekleşmeden backend tarafından hesaplanır. Gerçek
            değer sıfırsa yüzde tanımsızdır. Gösterim yuvarlanır; kaynak
            değerler aşağıda korunur.
          </p>
          <details className="technical-details">
            <summary>Model bilgisi, teknik referans ve tam hassasiyet</summary>
            <div className="stack">
              <RecordId id={p.id} label="Tahmin kaydı" />
              <h3>Model sınırlamaları ve kullanılan girdiler</h3>
              <ul>
                {p.prediction_limitations.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
              <pre className="raw-values">
                {JSON.stringify(
                  {
                    features: p.features,
                    comparison: p.comparison,
                    source_values: Object.fromEntries(
                      Object.keys(predictionLabels)
                        .filter((k) => k in p)
                        .map((k) => [k, p[k as keyof Prediction]]),
                    ),
                  },
                  null,
                  2,
                )}
              </pre>
            </div>
          </details>
        </div>
      </Section>
    </div>
  );
}
export function Predictions() {
  const data = useCatalog(),
    operations = useRecords<Operation>("/operations"),
    recipes = useRecords<Recipe>("/recipes"),
    models = useQuery({
      queryKey: ["prediction-models"],
      queryFn: () => request<{ models: ModelInfo[] }>("/predictions/models"),
      retry: false,
    });
  const [params, setParams] = useSearchParams(),
    [tab, setTab] = useState<"production" | "cutting">("production"),
    [lookup, setLookup] = useState(""),
    [lookupError, setLookupError] = useState(""),
    [history, setHistory] = useState(() => readHistory("predictions"));
  const selected = params.get("prediction") || "";
  const result = useQuery({
    queryKey: ["prediction", selected],
    queryFn: () => request<Prediction>("/predictions/" + selected),
    enabled: !!selected,
    retry: false,
  });
  const success = (r: unknown) => {
    const p = r as Prediction;
    remember("predictions", {
      id: p.id,
      at: p.predicted_at,
      label: p.kind === "production" ? "Üretim" : "Kuzu parçalama",
    });
    setHistory(readHistory("predictions"));
    setParams({ prediction: p.id });
  };
  const activeModel = models.data?.models.find(m => m.kind === tab);
  const info = models.data?.models.find(
    (m) => m.kind === (result.data?.kind || tab),
  );
  return (
    <div className="stack">
      <ModuleIntro
        title="Ölçülebilir tahmin. Açık sınırlar."
        description="Üretim ve parçalama öncesi karar desteği; gerçek sonuçla model sürümünü koruyarak karşılaştırın."
        icon={<Sparkles size={24} />}
      />
      {selected && (
        <State loading={result.isPending} error={result.error}>
          {result.data && <PredictionResult prediction={result.data} />}
        </State>
      )}
      <aside className="ai-data-note"><FlaskConical size={20}/><p><strong>6.000 SYNTHETIC kayıt</strong> · 3.000/model, gerçek tarihsel veri 0. Bazı EKP hata ölçümleri ve eski sabit test metrikleri geriledi; gerçek veri başarımı onaylanmadı. Tahmin kesin kayıt değildir.</p></aside>
      <details
        key={selected || "new"}
        open={!selected}
        className="technical-details prediction-form"
      >
        <summary>
          {selected ? "Yeni tahmin oluştur" : "Tahmin oluşturma"}
        </summary>
        <Section title="Yeni tahmin">
          <div className="tabs model-tabs" role="group" aria-label="Tahmin modeli">
            <button
              aria-pressed={tab === "production"} className={tab === "production" ? "active" : ""}
              onClick={() => setTab("production")}
            >
              Üretim verimi ve EKP
            </button>
            <button
              aria-pressed={tab === "cutting"} className={tab === "cutting" ? "active" : ""}
              onClick={() => setTab("cutting")}
            >
              Kuzu parçalama
            </button>
          </div>
          <State
            loading={
              data.loading ||
              operations.isPending ||
              recipes.isPending ||
              models.isPending
            }
            error={
              data.error || operations.error || recipes.error || models.error
            }
          >
            {!activeModel?.feature_schema ? <p className="notice">Model sınırları alınamadı; bağlantıyı yenileyin. Tahmin formu hazır değil.</p> : tab === "production" ? (
              <CommandForm
                schema={predictionSchemaForModel(productionPredictionSchema, activeModel)}
                defaults={{
                  operation_id: "",
                  output_product_id: "",
                  meat_type: "beef",
                  meat_kg: "",
                  spice_kg: "",
                  casing_kg: "",
                  meat_cost_eur: "",
                  spice_cost_eur: "",
                  casing_cost_eur: "",
                  planned_producer_profile: "producer_a",
                  package_weight_kg: "",
                  estimated_service_eur: "",
                }}
                path="/predictions/production"
                label="Üretim tahminini gözden geçir"
                confirmText="Sentetik modelle karar destek tahmini kaydedilecek. Bu işlem stok veya kesin maliyet üretmez."
                payload={productionPredictionPayload}
                onSuccess={success}
              >
                <ProductionFields
                  data={data}
                  model={activeModel}
                  operations={operations.data || []}
                />
              </CommandForm>
            ) : (
              <CommandForm
                schema={predictionSchemaForModel(cuttingPredictionSchema, activeModel)}
                defaults={{
                  operation_id: "",
                  recipe_version_id: "",
                  species: "Kuzu",
                  input_weight_kg: "",
                  part_products: {
                    leg: "",
                    shoulder: "",
                    back: "",
                    rib: "",
                    mince: "",
                  },
                }}
                path="/predictions/cutting"
                label="Kesim tahminini gözden geçir"
                confirmText="Beklenen parça ağırlıkları tahmin kaydı olarak saklanacak; fiilî tartım veya stok oluşturulmaz."
                payload={cuttingPredictionPayload}
                onSuccess={success}
              >
                <CuttingFields
                  data={data}
                  model={activeModel}
                  operations={operations.data || []}
                  recipes={recipes.data || []}
                />
              </CommandForm>
            )}
          </State>
        </Section>
      </details>
      <details className="technical-details">
        <summary>Tahmin geçmişi ve kayıt açma</summary>
        <Section
          title="Tahmin geçmişi ve kayıt açma"
          subtitle="Bu sekmede oluşturulan tahminler listelenir. Başka bir kaydı teknik referansıyla açabilirsiniz."
        >
          <form
            className="inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (!/^[0-9a-f-]{36}$/i.test(lookup)) {
                setLookupError("Geçerli bir tahmin kaydı kimliği girin.");
                return;
              }
              setLookupError("");
              setParams({ prediction: lookup });
            }}
          >
            <div className="field">
              <label htmlFor="prediction-lookup">Tahmin kaydı kimliği</label>
              <input
                id="prediction-lookup"
                value={lookup}
                onChange={(e) => { setLookup(e.target.value); setLookupError(""); }}
                placeholder="Örn: 00000000-0000-4000-8000-000000000001"
                autoComplete="off" aria-invalid={!!lookupError}
                aria-describedby={lookupError ? "prediction-lookup-help prediction-lookup-error" : "prediction-lookup-help"}
              />
              <small id="prediction-lookup-help">Tahmin ayrıntılarındaki tam kimliği kopyalayın.</small>
            </div>
            <button className="button">Tahmin kaydını aç</button>
          </form>
          {lookupError && (
            <p id="prediction-lookup-error" className="field-error" role="alert">
              {lookupError}
            </p>
          )}
          <Table
            headers={["Tür", "Tahmin zamanı", "Teknik referans", "Ayrıntı"]}
            empty={!history.length}
          >
            {history.map((h) => (
              <tr key={h.id}>
                <td>{h.label}</td>
                <td>{dateTime(h.at)}</td>
                <td className="code">{h.id}</td>
                <td>
                  <button
                    className="text-button"
                    onClick={() => setParams({ prediction: h.id })}
                  >
                    Tahmini aç
                  </button>
                </td>
              </tr>
            ))}
          </Table>
        </Section>
      </details>
      {info && (
        <details className="technical-details">
          <summary>Model ve teknik ayrıntılar · sentetik test metrikleri</summary>
          {result.data && result.data.model_version !== info.model_version && <p className="notice">Kayıtlı tahmin {result.data.model_version} sürümüne aittir. Aşağıdaki değerlendirme güncel {info.model_version} modelinindir; eski tahmin yeniden hesaplanmadı.</p>}
          <Section
            title="Sentetik test metrikleri"
            subtitle={`${info.model_version} · Gerçek işletme doğruluğu değildir; eğitim/validation/test: ${info.metrics.splits.train}/${info.metrics.splits.validation}/${info.metrics.splits.test}`}
          >
            <Table
              headers={[
                "Hedef",
                "Birim",
                "MAE",
                "RMSE",
                "Baseline MAE",
                "n test",
              ]}
            >
              {Object.entries(info.metrics.ridge_test).map(([key, m]) => (
                <tr key={key}>
                  <td>{key === 'predicted_yield_ratio' && info.kind === 'cutting' ? 'Kesim verimi' : predictionLabels[key]?.label || key}</td>
                  <td>{m.unit}</td>
                  <td>{displayDecimal(String(m.mae))}</td>
                  <td>{displayDecimal(String(m.rmse))}</td>
                  <td>
                    {displayDecimal(
                      String(info.metrics.baseline_test[key].mae),
                    )}
                  </td>
                  <td>{m.n}</td>
                </tr>
              ))}
            </Table>
            <details>
              <summary>Tam metrik değerleri</summary>
              <pre className="raw-values">
                {JSON.stringify(info.metrics, null, 2)}
              </pre>
            </details>
          </Section>
        </details>
      )}
    </div>
  );
}
