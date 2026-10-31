import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { Predictions, PredictionResult } from "../src/pages/Predictions";
import { productionPredictionSchema, cuttingPredictionSchema } from "../src/lib/module-validation";
import { predictionDomainIssues, predictionSchemaForModel } from "../src/lib/prediction-domain";
import type { ModelInfo, Prediction } from "../src/lib/modules";
import prod from "../../ml/models/production.json";
import cut from "../../ml/models/cutting.json";

const production = { ...prod.metadata, kind: "production", feature_schema: prod.feature_schema,
  input_constraints: prod.input_constraints, prediction_limitations: ["SYNTHETIC"] } as ModelInfo;
const cutting = { ...cut.metadata, kind: "cutting", feature_schema: cut.feature_schema,
  input_constraints: cut.input_constraints, prediction_limitations: ["SYNTHETIC"] } as ModelInfo;
const defaults = { ...prod.metadata.example_inputs, operation_id: "", output_product_id: "" };
const record: Prediction = { id: "00000000-0000-4000-8000-000000000001", kind: "production", operation_id: null,
  predicted_at: "2026-10-29T08:00:00Z", features: {}, context: {}, model_version: "production-ridge-v1-saved",
  data_origin: "SYNTHETIC", prediction_limitations: ["Gerçek işletme başarımı ölçülmedi."],
  predicted_finished_quantity: "21.50", predicted_yield_ratio: "0.80", predicted_total_cost_eur: "380", predicted_ekp_eur_per_unit: "17.67",
  comparison: { predicted_finished_quantity: { predicted: "21.50", actual: null, absolute_deviation: null, percentage_deviation: null } } };
function mockApi(write = vi.fn().mockResolvedValue(Response.json(record)), missing = false) {
  const fetch = vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method === "POST") return write(url, options);
    if (url.endsWith("/predictions/models")) return missing ? Response.json({ error: { code: "MODEL_UNAVAILABLE" } }, { status: 503 }) : Response.json({ models: [production, cutting] });
    if (url.includes("/predictions/")) return Response.json(record);
    return Response.json({ items: [], next_cursor: null });
  });
  vi.stubGlobal("fetch", fetch); return { fetch, write };
}
function mount(path = "/yapay-zeka") {
  return render(<MemoryRouter initialEntries={[path]}><QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><Predictions /></QueryClientProvider></MemoryRouter>);
}
afterEach(() => vi.unstubAllGlobals());

it("25 kg üretim yeni metadata ile kabul edilir; eski modelin aralığı sessizce genişletilmez", () => {
  expect(predictionSchemaForModel(productionPredictionSchema, production).safeParse(defaults).success).toBe(true);
  const old = { ...production, feature_schema: { ...production.feature_schema, meat_kg: { minimum: 60, maximum: 160, unit: "kg" } } };
  const rejected = predictionSchemaForModel(productionPredictionSchema, old).safeParse(defaults);
  expect(rejected.success).toBe(false);
  if (!rejected.success) expect(rejected.error.issues[0].message).toContain("60–160");
});

it.each(["4.999999", "300.000001", "NaN", "Infinity", "-1"])("geçersiz et miktarını alan bazında reddeder: %s", value => {
  const errors = predictionDomainIssues({ ...defaults, meat_kg: value }, production);
  expect(errors.some(e => e.field === "meat_kg" && e.message.includes("5–300"))).toBe(true);
});

it("malzeme miktarlarını seçili et miktarının desteklenen oranıyla doğrular, virgüllü ondalık kabul eder", () => {
  expect(predictionDomainIssues({ ...defaults, spice_kg: "0,5" }, production)).toEqual([]);
  expect(predictionDomainIssues({ ...defaults, spice_kg: "2" }, production)).toContainEqual({ field: "spice_kg", message: "Seçili et miktarı için 0,25–1 kg girin." });
});

it("üretim ekranı boş başlar, soluk örnek/metadata sınırı gösterir ve geçerli örneği doldurur", async () => {
  mockApi(); mount(); const user = userEvent.setup();
  const meat = await screen.findByLabelText("Planlanan et (kg)");
  expect(meat).toHaveValue(""); expect(meat).toHaveAttribute("placeholder", "Örn: 25");
  expect(screen.getByText("Desteklenen aralık 5–300 kg.")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Geçerli üretim örneğini doldur" }));
  expect(meat).toHaveValue("25"); expect(screen.getByLabelText("Planlanan baharat (kg)")).toHaveValue("0.5");
  await user.click(screen.getByRole("button", { name: "Üretim tahminini gözden geçir" }));
  expect(await screen.findByRole("dialog")).toBeVisible();
});

it("uygun reçete yoksa gerçek kurulum sayfalarına yönlendirir; örnek UUID veya ürün ilişkisi uydurmaz", async () => {
  mockApi(); mount(); const user = userEvent.setup();
  await screen.findByLabelText("Planlanan et (kg)");
  await user.click(screen.getByRole("button", { name: "Kuzu parçalama" }));
  expect(await screen.findByRole("link", { name: "Parçalama sayfasında reçete oluşturun" })).toHaveAttribute("href", "/parcalama");
  await user.click(screen.getByRole("button", { name: "Geçerli kesim örneğini doldur" }));
  expect(screen.getByLabelText("Tahmin giriş ağırlığı (kg)")).toHaveValue("25");
  expect(screen.getByLabelText("Tahmin reçete sürümü")).toHaveValue("");
  expect(screen.getByText("Desteklenen aralık 5–80 kg.")).toBeVisible();
});

it("backend aralık hatasını ilgili alana bağlar ve güncel sınırı gösterir", async () => {
  const message = "Planlanan et: 60–160 kg güncel model aralığında değer girin.";
  const write = vi.fn().mockResolvedValue(Response.json({ error: { code: "PREDICTION_OUT_OF_DOMAIN", message, details: { fields: [{ field: "meat_kg", message, minimum: 60, maximum: 160 }] } } }, { status: 422 }));
  mockApi(write); mount(); const user = userEvent.setup();
  await screen.findByLabelText("Planlanan et (kg)");
  await user.click(screen.getByRole("button", { name: "Geçerli üretim örneğini doldur" }));
  await user.click(screen.getByRole("button", { name: "Üretim tahminini gözden geçir" }));
  await user.click(await screen.findByRole("button", { name: "Onayla ve kaydet" }));
  await waitFor(() => expect(screen.getByLabelText("Planlanan et (kg)")).toHaveAttribute("aria-invalid", "true"));
  expect(screen.getByRole("alert")).toHaveTextContent("60–160 kg");
});

it("model eksikse tahmin formu veya sahte metrik/sonuç göstermez", async () => {
  mockApi(undefined, true); mount();
  expect(await screen.findByRole("alert")).toHaveTextContent("Tahmin üretilmedi");
  expect(screen.queryByLabelText("Planlanan et (kg)")).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Üretim tahmin sonucu" })).not.toBeInTheDocument();
});

it("eski tahmin sürümü görünür kalır; güncel model metrikleri eski kayda mal edilmez", async () => {
  mockApi(); mount("/yapay-zeka?prediction=" + record.id); const user = userEvent.setup();
  expect(await screen.findByText(record.model_version, { exact: true })).toBeVisible();
  expect(screen.getByText("Henüz gerçekleşmedi")).toBeVisible();
  await user.click(screen.getByText("Model ve teknik ayrıntılar · sentetik test metrikleri", { exact: true }));
  expect(screen.getByText(/eski tahmin yeniden hesaplanmadı/)).toBeVisible();
});

it("kesim sonucu beş parçayı karşılaştırma yüklenmeden de kg birimiyle gösterir", () => {
  render(<PredictionResult prediction={{ ...record, kind: "cutting", predicted_leg_kg: "6", predicted_shoulder_kg: "4", predicted_back_kg: "4", predicted_rib_kg: "5", predicted_mince_kg: "3", predicted_total_weight_kg: "22", predicted_difference_kg: "3" }} />);
  for (const name of ["Tahmini but", "Tahmini omuz", "Tahmini sırt", "Tahmini kaburga", "Tahmini kıyma"]) expect(screen.getByText(name)).toBeVisible();
  expect(screen.getByText("6 kg")).toBeVisible();
});
