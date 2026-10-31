import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { confirm, seedLamb, seedRecipe } from "./fixtures";
import type { Prediction, Recipe } from "../../src/lib/modules";
import type { Product } from "../../src/lib/types";
const artifacts = process.env.AVATAR_E2E_ARTIFACT_DIR || "test-results/ai-v2";
const productionLabels: Record<string, string> = { meat_kg: "Planlanan et (kg)", spice_kg: "Planlanan baharat (kg)", casing_kg: "Planlanan kılıf (kg)", meat_cost_eur: "Bilinen et maliyeti (EUR)", spice_cost_eur: "Bilinen baharat maliyeti (EUR)", casing_cost_eur: "Bilinen kılıf maliyeti (EUR)", package_weight_kg: "Paket ağırlığı (kg)", estimated_service_eur: "Hizmet ön teklifi (EUR)" };
function watch(page: Page) {
  page.on("pageerror", e => { throw e; });
  page.on("request", r => { if (r.url().includes("/api/")) expect(r.headers()["x-api-key"]).toBeUndefined(); });
}
async function capture(page: Page, name: string) {
  await mkdir(artifacts, { recursive: true });
  await page.screenshot({ path: artifacts + "/" + name + ".png", fullPage: true, animations: "disabled" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const checked = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const violations = checked.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => ({ target: n.target, summary: n.failureSummary })) }));
  await writeFile(artifacts + "/" + name + "-accessibility.json", JSON.stringify(violations, null, 2));
  expect(violations).toEqual([]);
}
async function submit(page: Page, kind: "production" | "cutting") {
  const response = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/predictions/" + kind));
  await confirm(page, kind === "production" ? "Üretim tahminini gözden geçir" : "Kesim tahminini gözden geçir");
  const result = await response; expect(result.status()).toBe(201);
  const record = await result.json() as Prediction;
  await expect(page).toHaveURL("/yapay-zeka?prediction=" + record.id);
  await expect(page.getByText(record.model_version, { exact: true })).toBeVisible();
  await expect(page.getByText("SYNTHETIC", { exact: true }).first()).toBeVisible();
  return record;
}

test("metadata örneğiyle 25 kg; küçük/100/büyük üretim; geçersiz giriş alan bazında reddedilir, mobil/desktop", async ({ page }) => {
  watch(page); await page.goto("/yapay-zeka");
  let calls = 0; page.on("request", r => { if (r.method() === "POST" && r.url().endsWith("/predictions/production")) calls++; });
  await expect(page.getByLabel("Planlanan et (kg)", { exact: true })).toHaveAttribute("placeholder", "Örn: 25");
  await expect(page.getByLabel("Planlanan et (kg)", { exact: true })).toHaveValue("");
  await page.getByRole("button", { name: "Geçerli üretim örneğini doldur", exact: true }).click();
  await page.getByLabel("Planlanan et (kg)", { exact: true }).fill("4");
  await page.getByRole("button", { name: "Üretim tahminini gözden geçir" }).click();
  await expect(page.getByLabel("Planlanan et (kg)", { exact: true })).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByText("Planlanan et: Desteklenen aralık 5–300 kg.", { exact: true })).toBeVisible();
  expect(calls).toBe(0);
  await page.getByLabel("Planlanan et (kg)", { exact: true }).fill("25");
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 }); await capture(page, "production-form-" + width);
  }
  const first = await submit(page, "production");
  expect(first.features.meat_kg).toBe("25"); expect(first.model_version).toContain("-ridge-v2-");
  expect(Number(first.predicted_finished_quantity)).toBeGreaterThan(0);
  expect(Number(first.predicted_ekp_eur_per_unit)).toBeGreaterThan(0);
  for (const weight of [5,100,300]) {
    await page.getByText("Yeni tahmin oluştur", { exact: true }).click();
    await page.getByRole("button", { name: "Geçerli üretim örneğini doldur", exact: true }).click();
    for (const [field, label] of Object.entries(productionLabels)) {
      if (field === "package_weight_kg") continue;
      const input = page.getByLabel(label, { exact: true });
      await input.fill(String(Number(await input.inputValue())*weight/25));
    }
    const next = await submit(page, "production");
    expect(next.features.meat_kg).toBe(String(weight));
    expect(Number(next.predicted_yield_ratio)).toBeGreaterThan(0);
    expect(Number(next.predicted_yield_ratio)).toBeLessThanOrEqual(1);
  }
  expect(calls).toBe(4);
  await capture(page, "production-result-1440");
});

test("gerçek beş ürün reçetesiyle 25/küçük/büyük kesim; parça, toplam ve fark görünür", async ({ page, request }) => {
  watch(page);
  let recipe: Recipe, parts: Record<string, Product>;
  if (process.env.AVATAR_AI_V2_SEED) {
    const seed = JSON.parse(await readFile(process.env.AVATAR_AI_V2_SEED, "utf8")); recipe = seed.recipe; parts = seed.parts;
  } else {
    const fixture = await seedLamb(request); recipe = await seedRecipe(request, fixture);
    parts = Object.fromEntries(fixture.parts.map(p => [p.key, p.product]));
  }
  await page.goto("/yapay-zeka");
  await page.getByRole("button", { name: "Kuzu parçalama", exact: true }).click();
  const names = { leg: "But", shoulder: "Omuz", back: "Sırt", rib: "Kaburga", mince: "Kıyma" };
  for (const [index, weight] of [25,5,80].entries()) {
    if (index) await page.getByText("Yeni tahmin oluştur", { exact: true }).click();
    await page.getByLabel("Tahmin reçete sürümü", { exact: true }).selectOption(recipe.id);
    await page.getByRole("button", { name: "Geçerli kesim örneğini doldur", exact: true }).click();
    await page.getByLabel("Tahmin giriş ağırlığı (kg)", { exact: true }).fill(String(weight));
    for (const [key, name] of Object.entries(names)) await page.getByLabel(name + " ürün eşlemesi", { exact: true }).selectOption(parts[key].id);
    const prediction = await submit(page, "cutting");
    expect(Number(prediction.predicted_total_weight_kg)).toBeLessThanOrEqual(weight);
    expect(Number(prediction.predicted_total_weight_kg)+Number(prediction.predicted_difference_kg)).toBeCloseTo(weight,6);
    for (const [key, name] of Object.entries(names)) {
      expect(Number(prediction[("predicted_" + key + "_kg") as keyof Prediction])).toBeGreaterThan(0);
      await expect(page.getByText("Tahmini " + name.toLocaleLowerCase("tr"), { exact: true })).toBeVisible();
    }
  }
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 }); await capture(page, "cutting-result-" + width);
  }
});

test("tahmin gerçek commit sonrası yanıt kaybı/reload aynı key/body; kayıt sürümü ve sonuç sabit", async ({ page }) => {
  watch(page); await page.goto("/yapay-zeka");
  await page.getByRole("button", { name: "Geçerli üretim örneğini doldur", exact: true }).click();
  const attempts: Array<{ key: string; body: string | null }> = [];
  let committed: Prediction | undefined;
  page.on("request", r => { if (r.method() === "POST" && r.url().endsWith("/predictions/production")) attempts.push({ key: r.headers()["idempotency-key"], body: r.postData() }); });
  await page.route("**/api/v1/predictions/production", async route => {
    const real = await route.fetch(); expect(real.status()).toBe(201);
    committed = await real.json() as Prediction; await route.abort("failed");
  });
  await confirm(page, "Üretim tahminini gözden geçir");
  await expect(page.getByRole("button", { name: "Aynı işlemi tekrar dene" })).toBeVisible();
  await page.unroute("**/api/v1/predictions/production");
  page.once("dialog", d => void d.accept()); await page.reload();
  await page.getByRole("button", { name: "Aynı işlemi tekrar dene", exact: true }).click();
  await expect(page).toHaveURL("/yapay-zeka?prediction=" + committed!.id);
  await expect(page.getByText(committed!.model_version, { exact: true })).toBeVisible();
  expect(attempts).toHaveLength(2); expect(attempts[0]).toEqual(attempts[1]);
  await page.reload();
  await expect(page.getByText(committed!.model_version, { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Üretim tahmin sonucu", exact: true })).toBeVisible();
});
