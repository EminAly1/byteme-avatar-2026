import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import AxeBuilder from "@axe-core/playwright";
import { api, apiAll, seedProduction, closeProduction, seedTrade } from "./fixtures";
import type { Lot, Party } from "../../src/lib/types";
import type { Recall, SaleDetail, ShipmentDetail } from "../../src/lib/modules";
const artifacts = process.env.AVATAR_E2E_ARTIFACT_DIR || "test-results/recall-safety";
const finalLabel = "Geri çağırmayı kesinleştir ve lotları bloke et";
async function choose(page: Page, id: string) {
  await page.goto("/geri-cagirma");
  await page.getByLabel("Sorunlu kaynak lot", { exact: true }).selectOption(id);
  await expect(page.getByRole("button", { name: "Gerekçe ve riske ilerle" })).toBeEnabled();
}
async function reason(page: Page) {
  await page.getByRole("button", { name: "Gerekçe ve riske ilerle" }).click();
  await page.getByLabel("Geri çağırma nedeni", { exact: true }).fill("KURGUSAL Görev21 kalite kontrol");
  await page.getByRole("button", { name: "Geri çağırmayı gözden geçir", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
}
async function shot(page: Page, name: string) {
  await mkdir(artifacts, { recursive: true });
  const modal = await page.getByRole("dialog").count() > 0;
  await page.screenshot({ path: `${artifacts}/${name}.png`, fullPage: !modal, animations: "disabled" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const results = await new AxeBuilder({ page }).include(".recall-wizard")
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const violations = results.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.map(n => ({ target: n.target, summary: n.failureSummary })) }));
  await writeFile(`${artifacts}/${name}-accessibility.json`, JSON.stringify(violations, null, 2));
  expect(violations).toEqual([]);
}
function watch(page: Page) {
  page.on("pageerror", e => { throw e; });
  page.on("request", r => {
    if (r.url().includes("/api/")) expect(r.headers()["x-api-key"]).toBeUndefined();
  });
}
async function sale(request: APIRequestContext, s: Awaited<ReturnType<typeof seedTrade>>) {
  return api<SaleDetail>(request, "/sales", { customer_id: s.customer.id,
    lines: [{ lot_id: s.lot, location_id: s.location.id, quantity: "1", unit: "kg", unit_price: "20.00" }] });
}

test("üç aşama, 390/768/1440, gerçek türev ve ikinci kademe; yanlış kod yazmaz, atomik blokaj satışı reddeder", async ({ page, request }) => {
  watch(page);
  const s = await seedProduction(request);
  await closeProduction(request, s);
  const lots = await apiAll<Lot>(request, "/lots");
  const root = lots.find(l => l.id === s.lots[0])!, finished = lots.find(l => l.external_code === s.p + "-SUC")!;
  const buyer = await api<Party>(request, "/parties", { name: s.p + " Market A", roles: ["customer"] });
  const next = await api<Party>(request, "/parties", { name: s.p + " Dağıtıcı X", roles: ["customer"] });
  const sold = await api<SaleDetail>(request, "/sales", { customer_id: buyer.id,
    lines: [{ lot_id: finished.id, location_id: s.location.id, quantity: "10", unit: "package", unit_price: "25.00" }] });
  const shipped = await api<ShipmentDetail>(request, "/shipments", { customer_id: buyer.id, sale_id: sold.id,
    lines: [{ sale_line_id: sold.lines[0].id, lot_id: finished.id, location_id: s.location.id, quantity: "10", unit: "package" }] });
  await api(request, "/distributions/second-tier", { source_shipment_line_id: shipped.lines[0].id,
    recipient_party_id: next.id, quantity: "4", unit: "package", distributed_at: shipped.shipped_at,
    reference: s.p + "-AX", evidence_note: "KURGUSAL Görev21 operatör bildirimi" });
  let writes = 0; page.on("request", r => { if (r.method() === "POST" && r.url().endsWith("/recalls")) writes++; });
  await choose(page, root.id);
  await expect(page.getByText(next.name, { exact: true })).toBeVisible();
  await expect(page.getByText("Bilinmiyor", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/fiziksel stok doğrulanmadı/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Etkilenen lotlar ve kayıtlı şirket stoğu" })).toBeVisible();
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await shot(page, `impact-${width}`);
  }
  expect(writes).toBe(0);
  expect((await api<Lot>(request, "/lots/" + root.id)).blocked).toBe(false);
  await page.getByRole("button", { name: "Gerekçe ve riske ilerle" }).click();
  await expect(page.getByRole("button", { name: "Geri çağırmayı gözden geçir" })).toBeDisabled();
  await page.getByLabel("Geri çağırma nedeni", { exact: true }).fill("KURGUSAL risk");
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 }); await shot(page, `risk-${width}`);
  }
  await page.getByRole("button", { name: "Geri çağırmayı gözden geçir" }).click();
  await expect(page.getByRole("button", { name: "Vazgeç" })).toBeFocused();
  const confirm = page.getByRole("button", { name: finalLabel });
  await expect(confirm).toBeDisabled();
  await page.getByLabel("Kaynak lot kodunu elle yazın").fill("YANLIS-LOT");
  await expect(confirm).toBeDisabled(); expect(writes).toBe(0);
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 }); await shot(page, `confirm-${width}`);
    expect(await page.getByRole("dialog").evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Geri çağırmayı gözden geçir" })).toBeFocused();
  expect(writes).toBe(0);
  await page.getByRole("button", { name: "Geri çağırmayı gözden geçir" }).click();
  await page.getByLabel("Kaynak lot kodunu elle yazın").fill(root.external_code);
  await confirm.focus(); await page.keyboard.press("Tab");
  await expect(page.getByLabel("Kaynak lot kodunu elle yazın")).toBeFocused();
  const response = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/recalls"));
  await confirm.click();
  const recalled = await (await response).json() as Recall;
  await expect(page).toHaveURL("/geri-cagirma/" + recalled.id);
  await expect(page.getByText("GERİ ÇAĞIRMA AKTİF")).toBeVisible();
  expect(recalled.report.lots.map(l => l.id).sort()).toEqual([root.id, finished.id].sort());
  expect(recalled.report.lots.every(l => l.blocked)).toBe(true);
  expect(recalled.report.total_shipped_quantities[0].quantity).toBe("10.000000");
  expect(recalled.report.second_tier_distributions[0].recipient_party_id).toBe(next.id);
  expect(recalled.report.unknown_distributions[0].market_remaining_quantity).toBeNull();
  expect((await api<Lot>(request, "/lots/" + s.lots[1])).blocked).toBe(false);
  const rejected = await request.post((process.env.AVATAR_E2E_API_URL || "http://127.0.0.1:8000") + "/v1/sales", {
    headers: { "X-API-Key": process.env.AVATAR_API_KEY!, "Idempotency-Key": crypto.randomUUID() },
    data: { customer_id: buyer.id, lines: [{ lot_id: finished.id, location_id: s.location.id, quantity: "1", unit: "package", unit_price: "25.00" }] },
  });
  expect(rejected.status()).toBe(409); expect((await rejected.json()).error.code).toBe("LOT_BLOCKED");
  expect(writes).toBe(1);
});

test("inceleme sonrası gerçek satış kapsamı değiştirir; backend reddeder ve yeni inceleme gerekir", async ({ page, request }) => {
  watch(page); const s = await seedTrade(request);
  const root = await api<Lot>(request, "/lots/" + s.lot);
  await choose(page, s.lot); await reason(page);
  await sale(request, s);
  await page.getByLabel("Kaynak lot kodunu elle yazın").fill(root.external_code);
  const stale = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/recalls"));
  await page.getByRole("button", { name: finalLabel }).click();
  const staleResponse = await stale;
  expect(staleResponse.status()).toBe(409); expect((await staleResponse.json()).error.code).toBe("RECALL_PREVIEW_STALE");
  await expect(page.getByText(/Kaynak veya etki kapsamı değişti/)).toBeVisible();
  await expect(page.getByLabel("Sorunlu kaynak lot")).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect((await api<Lot>(request, "/lots/" + s.lot)).blocked).toBe(false);
  await page.getByRole("button", { name: "Gerekçe ve riske ilerle" }).click();
  await expect(page.getByLabel("Geri çağırma nedeni", { exact: true })).toHaveValue("KURGUSAL Görev21 kalite kontrol");
  await page.getByRole("button", { name: "Geri çağırmayı gözden geçir" }).click();
  await expect(page.getByLabel("Kaynak lot kodunu elle yazın")).toHaveValue("");
  await page.getByLabel("Kaynak lot kodunu elle yazın").fill(root.external_code);
  await page.getByRole("button", { name: finalLabel }).click();
  await expect(page.getByText("GERİ ÇAĞIRMA AKTİF")).toBeVisible();
});

test("gerçek commit sonrası kayıp yanıt ve reload; aynı key/body ile aynı recall döner", async ({ page, request }) => {
  watch(page); const s = await seedTrade(request), root = await api<Lot>(request, "/lots/" + s.lot);
  const attempts: Array<{ key: string; body: string | null }> = [];
  let committed: Recall | undefined;
  page.on("request", r => { if (r.method() === "POST" && r.url().endsWith("/recalls")) attempts.push({ key: r.headers()["idempotency-key"], body: r.postData() }); });
  await choose(page, s.lot); await reason(page);
  await page.getByLabel("Kaynak lot kodunu elle yazın").fill(root.external_code);
  await page.route("**/api/v1/recalls", async route => {
    const real = await route.fetch(); expect(real.status()).toBe(201);
    committed = await real.json() as Recall;
    await route.abort("failed");
  });
  await page.getByRole("button", { name: finalLabel }).click();
  await expect(page.getByRole("button", { name: "Aynı işlemi tekrar dene" })).toBeVisible();
  expect(committed?.report.lots[0].blocked).toBe(true);
  await page.unroute("**/api/v1/recalls");
  page.on("dialog", d => void d.accept());
  await page.reload();
  await expect(page.getByLabel("Sorunlu kaynak lot")).toHaveCount(0);
  await page.getByRole("button", { name: "Aynı işlemi tekrar dene" }).click();
  await expect(page).toHaveURL("/geri-cagirma/" + committed!.id);
  expect(attempts).toHaveLength(2); expect(attempts[0]).toEqual(attempts[1]);
  expect((await api<Recall>(request, "/recalls/" + committed!.id)).id).toBe(committed!.id);
});
