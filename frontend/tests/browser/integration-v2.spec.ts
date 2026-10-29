const artifactDir = process.env.AVATAR_E2E_ARTIFACT_DIR || "validation-v2";
import { test, expect } from "@playwright/test";
import { writeFile, mkdir } from "node:fs/promises";
import {
  api,
  apiAll,
  confirm,
  seedLamb,
  seedRecipe,
  seedTrade,
  seedProduction,
  closeProduction,
  closeCutting,
  stock,
  prefix,
} from "./fixtures";
import { displayDecimal } from "../../src/lib/presentation";
import type {
  Cutting,
  Recipe,
  SaleDetail,
  ShipmentDetail,
  Prediction,
  Recall,
  TraceReport,
} from "../../src/lib/modules";
import type { Lot, Operation } from "../../src/lib/types";
const evidence: Array<Record<string, unknown>> = [];
async function capture(page: import("@playwright/test").Page, name: string) {
  await mkdir(artifactDir + "/screenshots", { recursive: true });
  await page.screenshot({
    path: artifactDir + "/screenshots/" + name + ".png",
    fullPage: true,
  });
}
test.beforeEach(async ({ page }) => {
  page.on("pageerror", (error) => {
    throw new Error("Browser runtime error: " + error.message);
  });
  page.on("request", (r) => {
    if (r.url().includes("/api/"))
      expect(r.headers()["x-api-key"]).toBeUndefined();
  });
});
test.afterAll(async () => {
  await mkdir(artifactDir, { recursive: true });
  await writeFile(
    artifactDir + "/acceptance.json",
    JSON.stringify(evidence, null, 2) + "\n",
  );
});

test("reçete UI → quantity/value kesimleri; eksik açıklama ve gerçek backend 422; iki ayrı kaynak lot", async ({
  page,
  request,
}) => {
  const s = await seedLamb(request),
    results: Cutting[] = [];
  for (const [index, method] of ["quantity", "value"].entries()) {
    await page.goto("/parcalama");
    await page
      .getByRole("button", { name: "Yeni reçete", exact: true })
      .click();
    await page.getByLabel("Reçete kodu", { exact: true }).fill(s.p + "-KEY");
    await page
      .getByLabel("Reçete sürümü", { exact: true })
      .fill(String(index + 1));
    await page
      .getByLabel("Kaynak kuzu ürünü", { exact: true })
      .selectOption(s.source.id);
    await page
      .getByLabel("Maliyet dağıtım yöntemi", { exact: true })
      .selectOption(method);
    for (let i = 0; i < 5; i++) {
      if (i)
        await page
          .getByRole("button", { name: "Reçete parçası ekle", exact: true })
          .click();
      await page
        .getByLabel("Parça ürünü " + (i + 1), { exact: true })
        .selectOption(s.parts[i].product.id);
      await page
        .getByLabel("Referans EUR/kg " + (i + 1), { exact: true })
        .fill(s.parts[i].reference);
    }
    const recipeResponse = page.waitForResponse(
      (r) =>
        r.request().method() === "POST" && r.url().endsWith("/api/v1/recipes"),
    );
    await confirm(page, "Reçeteyi kaydet");
    const recipe = (await (await recipeResponse).json()) as Recipe;
    expect(recipe.version).toBe(index + 1);
    await page
      .getByLabel("Kesim numarası", { exact: true })
      .fill(s.p + "-CUT-" + index);
    await page
      .getByLabel("Kesim reçetesi", { exact: true })
      .selectOption(recipe.id);
    const draftResponse = page.waitForResponse(
      (r) =>
        r.request().method() === "POST" && r.url().endsWith("/api/v1/cuttings"),
    );
    await confirm(page, "Kesim taslağı oluştur");
    const c = (await (await draftResponse).json()) as Cutting;
    await expect(page).toHaveURL("/parcalama/" + c.id);
    await page
      .getByLabel("Kaynak kuzu lotu / konum", { exact: true })
      .selectOption(s.lots[index] + "|" + s.location.id);
    await page.getByLabel("Kesime alınan kg", { exact: true }).fill("25");
    await page
      .getByLabel("Parça kabul deposu", { exact: true })
      .selectOption(s.location.id);
    for (let i = 0; i < c.allocation_snapshot.lines.length; i++) {
      const p = s.parts.find(
        (p) => p.product.id === c.allocation_snapshot.lines[i].product_id,
      )!;
      await page
        .getByLabel("Parça kg " + (i + 1), { exact: true })
        .fill(p.weight);
      await page
        .getByLabel("Parça lot kodu " + (i + 1), { exact: true })
        .fill(s.p + "-" + method + "-" + p.key);
    }
    await page
      .getByRole("button", { name: "Kesimi kapat", exact: true })
      .click();
    await expect(page.getByText(/Giriş kg, mamul/)).toBeVisible();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await page
      .getByRole("button", { name: "Açıklanmış fark ekle", exact: true })
      .click();
    await page.getByLabel("Fark kg 1", { exact: true }).fill("3");
    await page
      .getByRole("button", { name: "Kesimi kapat", exact: true })
      .click();
    await expect(
      page.getByLabel("Fark nedeni 1", { exact: true }),
    ).toHaveAttribute("aria-invalid", "true");
    await page
      .getByLabel("Fark nedeni 1", { exact: true })
      .fill("KURGUSAL E2E test ölçümü; gerçek işletme verisi değildir.");
    if (index === 0) {
      await page.route("**/api/v1/cuttings/*/post", async (route) => {
        const body = route.request().postDataJSON();
        body.differences[0].quantity = "2";
        await route.continue({ postData: JSON.stringify(body) });
      });
      await confirm(page, "Kesimi kapat");
      await expect(page.getByRole("alert")).toContainText("dengelenmiyor");
      expect(await stock(request, s.lots[index], s.location.id)).toBe(
        "25.000000",
      );
      await page.unroute("**/api/v1/cuttings/*/post");
    }
    const closedResponse = page.waitForResponse(
      (r) => r.request().method() === "POST" && r.url().endsWith("/post"),
    );
    await confirm(page, "Kesimi kapat");
    const closed = (await (await closedResponse).json()) as Cutting;
    expect(closed.total_cost).toBe("287.500000");
    expect(closed.outputs).toHaveLength(5);
    results.push(closed);
    await expect(
      page.getByRole("heading", {
        name: "Parça lotları ve maliyetler",
        exact: true,
      }),
    ).toBeVisible();
    expect(await stock(request, s.lots[index], s.location.id)).toBe("0.000000");
  }
  expect(results[0].outputs.map((o) => o.allocated_cost)).not.toEqual(
    results[1].outputs.map((o) => o.allocated_cost),
  );
  await capture(page, "cutting-desktop");
  await page.setViewportSize({ width: 390, height: 844 });
  await capture(page, "cutting-mobile");
  evidence.push({
    scenario: "two independent 25 kg cuts",
    source_lots: s.lots,
    cutting_ids: results.map((r) => r.id),
    cost_each: "287.500000",
    backend_422_verified: true,
  });
});

test("lotlu UI satış → bağlı sevkiyat aynı hareket; bağımsız sevkiyat yeni çıkış", async ({
  page,
  request,
}) => {
  const s = await seedTrade(request);
  await page.goto("/satislar");
  await page.getByRole("button", { name: "Yeni satış", exact: true }).click();
  await page.getByLabel("Müşteri", { exact: true }).selectOption(s.customer.id);
  await page
    .getByLabel("Lot / konum 1", { exact: true })
    .selectOption(s.lot + "|" + s.location.id);
  await page.getByLabel("Miktar 1", { exact: true }).fill("1");
  await page.getByLabel("Birim fiyat 1 (EUR)", { exact: true }).fill("25,00");
  const saleResponse = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/sales"),
  );
  await confirm(page, "Satışı gözden geçir");
  const sale = (await (await saleResponse).json()) as SaleDetail;
  await expect(page).toHaveURL("/satislar/" + sale.id);
  expect(await stock(request, s.lot, s.location.id)).toBe("9.000000");
  await page.locator('summary').filter({hasText:'Stok hareketi'}).click();
  await expect(
    page.getByText(sale.lines[0].stock_movement_id, { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", {
      name: "Bu satışa bağlı sevkiyat oluştur",
      exact: true,
    })
    .click();
  await expect(
    page.getByText(/Bağlı sevkiyat satışın stok hareketini paylaşır/),
  ).toBeVisible();
  const shipResponse = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/shipments"),
  );
  await confirm(page, "Bağlı sevkiyatı gözden geçir");
  const shipment = (await (await shipResponse).json()) as ShipmentDetail;
  expect(shipment.lines[0].stock_movement_id).toBe(
    sale.lines[0].stock_movement_id,
  );
  expect(await stock(request, s.lot, s.location.id)).toBe("9.000000");
  await expect(page.getByRole("dialog")).toBeVisible();
  // The POST response can arrive before the new native modal receives focus.
  // Exercise Escape only after its focus target is ready, then verify closure.
  const closeShipment = page.getByRole('button', {name:'Ayrıntıyı kapat',exact:true});
  await expect(closeShipment).toBeFocused();
  await closeShipment.press('Escape');
  await expect(page.getByRole('dialog')).toBeHidden();
  const openShipment = page.getByRole('row').filter({hasText:s.customer.name}).getByRole('button',{name:'Sevkiyatı aç',exact:true});
  await openShipment.click();
  await expect(page.getByRole('button',{name:'Ayrıntıyı kapat',exact:true})).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(page.getByRole('dialog').locator('summary').filter({hasText:'Stok hareketi'}).last()).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button',{name:'Ayrıntıyı kapat',exact:true})).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(openShipment).toBeFocused();
  await page
    .getByRole("button", { name: "Bağımsız sevkiyat", exact: true })
    .click();
  await page.getByLabel("Müşteri", { exact: true }).selectOption(s.customer.id);
  await page
    .getByLabel("Lot / konum 1", { exact: true })
    .selectOption(s.lot + "|" + s.location.id);
  await page.getByLabel("Miktar 1", { exact: true }).fill("2");
  await confirm(page, "Bağımsız sevkiyatı gözden geçir");
  await expect
    .poll(() => stock(request, s.lot, s.location.id))
    .toBe("7.000000");
  evidence.push({
    scenario: "sale + linked + independent shipment",
    sale_id: sale.id,
    shipment_id: shipment.id,
    shared_movement: sale.lines[0].stock_movement_id,
    stock: "10→9→9→7",
  });
});

test("gerçek ileri/geri izleme ve ET recall → Market A/B/C 30/25/30; onay şart", async ({
  page,
  request,
}) => {
  const lots = await apiAll<Lot>(request, "/lots");
  const root = lots.find((l) => l.external_code === "ET-2026-001")!,
    finished = lots.find((l) => l.external_code === "SUC-2026-045")!;
  expect(root).toBeTruthy();
  await page.goto("/izlenebilirlik?lot=" + root.id);
  await expect(
    page.getByRole("heading", {
      name: "Kaynak lotun ileri kayıt zinciri",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText("85 paket", { exact: true })).toBeVisible();
  await capture(page, "trace-desktop");
  await page
    .getByLabel("İzlenecek lot", { exact: true })
    .selectOption(finished.id);
  await page
    .getByLabel("İzleme yönü", { exact: true })
    .selectOption("backward");
  await expect(
    page.getByRole("heading", {
      name: "Kaynaklara doğru kayıt zinciri",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("ET-2026-001", { exact: true }).first(),
  ).toBeVisible();
  await page.goto("/geri-cagirma");
  await page
    .getByLabel("Sorunlu kaynak lot", { exact: true })
    .selectOption(root.id);
  await expect(
    page.getByText(/henüz kesinleşmiş recall sonucu değildir/),
  ).toBeVisible();
  let calls = 0;
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith("/recalls")) calls++;
  });
  await page.getByRole("button", { name: "Gerekçe ve riske ilerle", exact: true }).click();
  await page
    .getByLabel("Geri çağırma nedeni", { exact: true })
    .fill("KURGUSAL E2E kalite kontrolü");
  await page
    .getByRole("button", { name: "Geri çağırmayı gözden geçir", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(calls).toBe(0);
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", {
      name: "Geri çağırmayı gözden geçir",
      exact: true,
    }),
  ).toBeFocused();
  expect(calls).toBe(0);
  const response = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/recalls"),
  );
  await page.getByRole("button", { name: "Geri çağırmayı gözden geçir", exact: true }).click();
  await page.getByLabel("Kaynak lot kodunu elle yazın").fill(root.external_code);
  await page.getByRole("button", { name: "Geri çağırmayı kesinleştir ve lotları bloke et", exact: true }).click();
  const recall = (await (await response).json()) as Recall;
  await expect(page).toHaveURL("/geri-cagirma/" + recall.id);
  await expect(page.getByText("GERİ ÇAĞIRMA AKTİF")).toBeVisible();
  expect(recall.report.buyers).toHaveLength(3);
  expect(recall.report.total_shipped_quantities[0].quantity).toBe("85.000000");
  expect(
    recall.report.buyers
      .flatMap((b) => b.quantities.map((q) => q.shipped_quantity))
      .sort(),
  ).toEqual(["25.000000", "30.000000", "30.000000"]);
  for (const buyer of recall.report.buyers)
    await expect(
      page.getByRole("heading", {
        name: buyer.current_customer.name,
        exact: true,
      }),
    ).toBeVisible();
  await expect(
    page.getByText("Bilinmiyor", { exact: true }).first(),
  ).toBeVisible();
  expect((await api<Lot>(request, "/lots/" + finished.id)).blocked).toBe(true);
  await capture(page, "recall-desktop");
  evidence.push({
    scenario: "trace/recall canonical demo",
    recall_id: recall.id,
    total_shipped: "85.000000",
    markets: 3,
  });
});

test("stale lot seçimi sonrası gerçek LOT_BLOCKED; süresi geçmiş lot seçenekleri kapalı", async ({
  page,
  request,
}) => {
  const s = await seedTrade(request),
    expired = await seedTrade(request, "2020-01-01");
  await page.goto("/satislar");
  await page.getByRole("button", { name: "Yeni satış", exact: true }).click();
  await page.getByLabel("Müşteri", { exact: true }).selectOption(s.customer.id);
  const lot = page.getByLabel("Lot / konum 1", { exact: true });
  await expect(
    lot.locator(`option[value="${expired.lot}|${expired.location.id}"]`),
  ).toBeDisabled();
  await lot.selectOption(s.lot + "|" + s.location.id);
  await page.getByLabel("Miktar 1", { exact: true }).fill("1");
  await page.getByLabel("Birim fiyat 1 (EUR)", { exact: true }).fill("25");
  await api(request, "/recalls", {
    source_lot_id: s.lot,
    reason: "KURGUSAL stale cache yarışı",
  });
  await confirm(page, "Satışı gözden geçir");
  await expect(page.getByRole("alert")).toContainText(
    "geri çağırma kapsamında bloke",
  );
  expect(await stock(request, s.lot, s.location.id)).toBe("10.000000");
  await page.reload();
  await page.getByRole("button", { name: "Yeni satış", exact: true }).click();
  await expect(
    page
      .getByLabel("Lot / konum 1", { exact: true })
      .locator(`option[value="${s.lot}|${s.location.id}"]`),
  ).toBeDisabled();
  evidence.push({
    scenario: "stale LOT_BLOCKED and expired selector",
    blocked_lot: s.lot,
    stock_unchanged: "10.000000",
  });
});

test("gerçek commit sonrası kayıp cevap: reload ve aynı UUID/gövde ile retry tek satış üretir", async ({
  page,
  request,
}) => {
  const s = await seedTrade(request);
  await page.goto("/satislar");
  await page.getByRole("button", { name: "Yeni satış", exact: true }).click();
  await page.getByLabel("Müşteri", { exact: true }).selectOption(s.customer.id);
  await page
    .getByLabel("Lot / konum 1", { exact: true })
    .selectOption(s.lot + "|" + s.location.id);
  await page.getByLabel("Miktar 1", { exact: true }).fill("1");
  await page.getByLabel("Birim fiyat 1 (EUR)", { exact: true }).fill("25");
  const attempts: Array<{ key: string | undefined; body: string | null }> = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith("/sales"))
      attempts.push({
        key: r.headers()["idempotency-key"],
        body: r.postData(),
      });
  });
  let first: SaleDetail | undefined;
  await page.route("**/api/v1/sales", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    first = await response.json();
    await route.abort("failed");
  });
  await confirm(page, "Satışı gözden geçir");
  await expect(
    page.getByRole("button", { name: "Aynı işlemi tekrar dene", exact: true }),
  ).toBeVisible();
  expect(await stock(request, s.lot, s.location.id)).toBe("9.000000");
  await page.unroute("**/api/v1/sales");
  page.once("dialog", (d) => d.accept());
  await page.reload();
  await page
    .getByRole("button", { name: "Aynı işlemi tekrar dene", exact: true })
    .click();
  await expect(page).toHaveURL("/satislar/" + first!.id);
  expect(attempts).toHaveLength(2);
  expect(attempts[0]).toEqual(attempts[1]);
  expect(await stock(request, s.lot, s.location.id)).toBe("9.000000");
  evidence.push({
    scenario: "real commit/lost HTTP response/retry",
    sale_id: first!.id,
    same_key: true,
    same_body: true,
    stock_after_both: "9.000000",
  });
});

test("üretim ML UI: gerçek forecast UUID → kapanış sonrası 85 paket ve Decimal sapma", async ({
  page,
  request,
}) => {
  const s = await seedProduction(request);
  await page.goto("/yapay-zeka");
  for (const [label, value] of [
    ["Planlanan et (kg)", "100"],
    ["Planlanan baharat (kg)", "2"],
    ["Planlanan kılıf (kg)", "5"],
    ["Bilinen et maliyeti (EUR)", "970"],
    ["Bilinen baharat maliyeti (EUR)", "48"],
    ["Bilinen kılıf maliyeti (EUR)", "58"],
    ["Paket ağırlığı (kg)", "1"],
    ["Hizmet ön teklifi (EUR)", "450"],
  ])
    await page.getByLabel(label, { exact: true }).fill(value);
  await page
    .getByLabel("Üretim operasyon referansı", { exact: true })
    .selectOption(s.op.id);
  await page
    .getByLabel("Tahminin paket ürünü", { exact: true })
    .selectOption(s.output.id);
  const response = page.waitForResponse(
    (r) =>
      r.request().method() === "POST" &&
      r.url().endsWith("/predictions/production"),
  );
  await confirm(page, "Üretim tahminini gözden geçir");
  const prediction = (await (await response).json()) as Prediction;
  expect(prediction.features).not.toHaveProperty("actual_finished_quantity");
  await expect(
    page.getByText("Henüz gerçekleşmedi", { exact: true }).first(),
  ).toBeVisible();
  await closeProduction(request, s);
  await page.getByRole("button", { name: "Yenile", exact: true }).click();
  const row = page
    .getByRole("row")
    .filter({ hasText: "Mamul miktarı" });
  await expect(row.getByRole("cell", { name: displayDecimal(prediction.predicted_finished_quantity!) + " paket", exact: true })).toBeVisible();
  await expect(
    row.getByRole("cell", { name: "85 paket", exact: true }),
  ).toBeVisible();
  await page.getByText('Model bilgisi, teknik referans ve tam hassasiyet',{exact:true}).click();
  await page.locator('summary').filter({hasText:'Tahmin kaydı'}).click();
  await expect(page.getByText(prediction.id,{exact:true}).first()).toBeVisible();
  await capture(page, "ai-production-desktop");
  evidence.push({
    scenario: "production ML UI + actual API closure",
    prediction_id: prediction.id,
    operation_id: s.op.id,
    actual_quantity: "85.000000",
  });
});

test("kesim ML UI: beş gerçek ürün eşlemesi ve 25 kg tahmin/gerçek/sapma", async ({
  page,
  request,
}) => {
  const s = await seedLamb(request),
    recipe = await seedRecipe(request, s),
    cutting = await api<Operation>(request, "/cuttings", {
      code: s.p + "-CUT",
      recipe_version_id: recipe.id,
    });
  await page.goto("/yapay-zeka");
  await page
    .getByRole("button", { name: "Kuzu parçalama", exact: true })
    .click();
  await page
    .getByLabel("Tahmin reçete sürümü", { exact: true })
    .selectOption(recipe.id);
  await page
    .getByLabel("Tahmin giriş ağırlığı (kg)", { exact: true })
    .fill("25");
  await page
    .getByLabel("Kesim operasyon referansı", { exact: true })
    .selectOption(cutting.id);
  for (const p of s.parts)
    await page
      .getByLabel(p.name + " ürün eşlemesi", { exact: true })
      .selectOption(p.product.id);
  const response = page.waitForResponse(
    (r) =>
      r.request().method() === "POST" &&
      r.url().endsWith("/predictions/cutting"),
  );
  await confirm(page, "Kesim tahminini gözden geçir");
  const prediction = (await (await response).json()) as Prediction;
  await expect(
    page.getByText("Henüz gerçekleşmedi", { exact: true }).first(),
  ).toBeVisible();
  await closeCutting(request, s, cutting);
  await page.getByRole("button", { name: "Yenile", exact: true }).click();
  const row = page
    .getByRole("row")
    .filter({ hasText: "Toplam parça ağırlığı" });
  await expect(
    row.getByRole("cell", { name: "22 kg", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/Bu model sentetik verilerle eğitilmiştir/).first(),
  ).toBeVisible();
  await capture(page, "ai-cutting-desktop");
  await page.setViewportSize({ width: 390, height: 844 });
  await capture(page, "ai-mobile");
  evidence.push({
    scenario: "cutting ML UI + actual API closure",
    prediction_id: prediction.id,
    operation_id: cutting.id,
    actual_kg: "22.000000",
  });
});

test("beş viewport: gerçek modüller, mobil satış ve drawer klavye erişimi; sayfa taşmaz", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  const s = await seedTrade(request);
  for (const viewport of [
    { width: 360, height: 800 },
    { width: 390, height: 844 },
    { width: 768, height: 1024 },
    { width: 1024, height: 768 },
    { width: 1440, height: 900 },
  ]) {
    await page.setViewportSize(viewport);
    for (const route of [
      "/",
      "/parcalama",
      "/satislar",
      "/sevkiyatlar",
      "/izlenebilirlik",
      "/geri-cagirma",
      "/yapay-zeka",
    ]) {
      await page.goto(route);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.getByText("Kayıtlar yükleniyor…")).toHaveCount(0, {
        timeout: 20000,
      });
      await expect(page.getByRole("alert")).toHaveCount(0);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        route + " " + viewport.width,
      ).toBe(true);
    }
    if (viewport.width === 390) {
      await page.goto("/");
      await capture(page, "dashboard-mobile");
      await page
        .getByRole("button", { name: "Menüyü aç", exact: true })
        .click();
      await expect(
        page.getByRole("button", { name: "Menüyü kapat", exact: true }),
      ).toBeFocused();
      await page.keyboard.press('Shift+Tab');
      await expect(page.locator('.sidebar .brand')).toBeFocused();
      await page.keyboard.press('Shift+Tab');
      await expect(page.getByRole('link',{name:'Stoklar',exact:true})).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.locator('.sidebar .brand')).toBeFocused();
      await page.keyboard.press("Escape");
      await expect(
        page.getByRole("button", { name: "Menüyü aç", exact: true }),
      ).toBeFocused();
      await page.goto("/satislar");
      await page
        .getByRole("button", { name: "Yeni satış", exact: true })
        .click();
      await page
        .getByLabel("Müşteri", { exact: true })
        .selectOption(s.customer.id);
      await page
        .getByLabel("Lot / konum 1", { exact: true })
        .selectOption(s.lot + "|" + s.location.id);
      await page.getByLabel("Miktar 1", { exact: true }).fill("1");
      await page.getByLabel("Birim fiyat 1 (EUR)", { exact: true }).fill("25");
      await capture(page, "sale-mobile");
      await page.getByRole('button',{name:'Satışı gözden geçir',exact:true}).click();
      await expect(page.getByRole('button',{name:'Vazgeç',exact:true})).toBeFocused();
      await page.keyboard.press('Shift+Tab');
      await expect(page.getByRole('button',{name:'Onayla ve kaydet',exact:true})).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.getByRole('button',{name:'Vazgeç',exact:true})).toBeFocused();
      await page.keyboard.press('Escape');
      await expect(page.getByRole('button',{name:'Satışı gözden geçir',exact:true})).toBeFocused();
      await confirm(page, "Satışı gözden geçir");
      await expect(page).toHaveURL(/\/satislar\/[0-9a-f-]+/);
    }
    if (viewport.width === 1440) {
      await page.goto("/");
      await capture(page, "dashboard-desktop");
    }
    if (viewport.width === 768) {
      await page.goto("/parcalama");
      await capture(page, "cutting-tablet");
    }
  }
  const secret = process.env.AVATAR_API_KEY!;
  // Inspect returned browser text in Node. Never pass the secret into page.evaluate.
  const browserText = await page.evaluate(() => [document.documentElement.innerHTML, JSON.stringify(localStorage), JSON.stringify(sessionStorage)]);
  expect(browserText.some(text => text.includes(secret))).toBe(false);
  for (const [old, next] of [
    ["parcalama", "parcalama"],
    ["satis", "satislar"],
    ["izleme", "izlenebilirlik"],
    ["recall", "geri-cagirma"],
    ["ai", "yapay-zeka"],
  ]) {
    await page.goto("/plan/" + old);
    await expect(page).toHaveURL("/" + next);
  }
  evidence.push({
    scenario: "responsive",
    viewports: ["360x800", "390x844", "768x1024", "1024x768", "1440x900"],
    mobile_sale: true,
    keyboard_menu: true,
    legacy_redirects: 5,
  });
});

test("yan ürün ayrı lot/stok; diğer kayıp açıklaması ve reçete kullanılabilirliği gerçek UI", async ({
  page,
  request,
}) => {
  const s = await seedLamb(request);
  const byproduct = await api<import("../../src/lib/types").Product>(
    request,
    "/products",
    {
      sku: s.p + "-BY",
      name: s.p + " Yan ürün",
      type: "byproduct",
      base_unit: "kg",
    },
  );
  const recipe = await api<Recipe>(request, "/recipes", {
    code: s.p + "-BY-KEY",
    version: 1,
    species: "Kuzu",
    input_product_id: s.source.id,
    allocation_method: "quantity",
    lines: [
      ...s.parts.map((p) => ({ product_id: p.product.id })),
      { product_id: byproduct.id },
    ],
  });
  const c = await api<Cutting>(request, "/cuttings", {
    code: s.p + "-BY-CUT",
    recipe_version_id: recipe.id,
  });
  await page.goto("/parcalama/" + c.id);
  await page
    .getByLabel("Kaynak kuzu lotu / konum", { exact: true })
    .selectOption(s.lots[0] + "|" + s.location.id);
  await page.getByLabel("Kesime alınan kg", { exact: true }).fill("25");
  await page
    .getByLabel("Parça kabul deposu", { exact: true })
    .selectOption(s.location.id);
  let byIndex = 0;
  for (let i = 0; i < c.allocation_snapshot.lines.length; i++) {
    const line = c.allocation_snapshot.lines[i],
      isBy = line.product_id === byproduct.id;
    const p = s.parts.find((p) => p.product.id === line.product_id);
    await page
      .getByLabel("Parça kg " + (i + 1), { exact: true })
      .fill(isBy ? "2" : p!.weight);
    await page
      .getByLabel("Parça lot kodu " + (i + 1), { exact: true })
      .fill(s.p + "-LOT-" + i);
    if (isBy) byIndex = i;
  }
  await page
    .getByRole("button", { name: "Açıklanmış fark ekle", exact: true })
    .click();
  await page
    .getByLabel("Fark türü 1", { exact: true })
    .selectOption("other_loss");
  await page.getByLabel("Fark kg 1", { exact: true }).fill("1");
  await page
    .getByLabel("Fark nedeni 1", { exact: true })
    .fill("KURGUSAL ölçülmüş diğer kayıp");
  await page.getByRole("button", { name: "Kesimi kapat", exact: true }).click();
  await expect(
    page.getByLabel("Parça açıklaması " + (byIndex + 1), { exact: true }),
  ).toHaveAttribute("aria-invalid", "true");
  await page
    .getByLabel("Parça açıklaması " + (byIndex + 1), { exact: true })
    .fill("KURGUSAL stoklanacak yan ürün");
  const response = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/post"),
  );
  await confirm(page, "Kesimi kapat");
  const result = (await (await response).json()) as Cutting;
  expect(result.differences[0].kind).toBe("other_loss");
  const output = result.outputs.find(
    (o) => o.explanation === "KURGUSAL stoklanacak yan ürün",
  )!;
  expect(await stock(request, output.lot_id, s.location.id)).toBe("2.000000");
  expect(result.total_cost).toBe("287.500000");
  await page.goto("/parcalama");
  const card = page.locator(".record-card").filter({ hasText: recipe.code });
  await card
    .getByRole("button", { name: "Kullanılabilirlik", exact: true })
    .click();
  await confirm(page, "Sürümü kullanıma kapat");
  await expect(
    card.getByText("Kullanıma kapalı", { exact: true }),
  ).toBeVisible();
  expect((await api<Cutting>(request, "/cuttings/" + c.id)).total_cost).toBe(
    "287.500000",
  );
  evidence.push({
    scenario: "byproduct/other_loss/recipe availability",
    cutting_id: c.id,
    byproduct_lot: output.lot_id,
    byproduct_stock: "2.000000",
    other_loss: "1.000000",
    original_cost_preserved: true,
  });
});
