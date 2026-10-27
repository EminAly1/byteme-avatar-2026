import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import {
  api,
  apiAll,
  closeProduction,
  confirm,
  prefix,
  seedProduction,
  seedTrade,
  stock,
} from "./fixtures";
import type {
  Party,
  Location,
  ReceiptDetail,
  OperationDetail,
  Product,
} from "../../src/lib/types";
import type { SaleDetail, ShipmentDetail, Recall } from "../../src/lib/modules";
import type {
  Correction,
  Profitability,
  Rework,
  SecondTier,
  Transfer,
} from "../../src/lib/operational-types";

async function sell(
  request: APIRequestContext,
  s: Awaited<ReturnType<typeof seedTrade>>,
  quantity = "5",
) {
  return api<SaleDetail>(request, "/sales", {
    customer_id: s.customer.id,
    lines: [
      {
        lot_id: s.lot,
        location_id: s.location.id,
        quantity,
        unit: "kg",
        unit_price: "20",
      },
    ],
  });
}
async function ship(request: APIRequestContext, sale: SaleDetail) {
  return api<ShipmentDetail>(request, "/shipments", {
    customer_id: sale.customer_id,
    sale_id: sale.id,
    lines: sale.lines.map((line) => ({
      sale_line_id: line.id,
      lot_id: line.lot_id,
      location_id: line.location_id,
      quantity: line.quantity,
      unit: line.unit,
    })),
  });
}
async function trade20(request: APIRequestContext) {
  const s = await seedTrade(request);
  const receipt = await api<ReceiptDetail>(request, "/receipts", {
    supplier_id: s.supplier.id,
    location_id: s.location.id,
    lines: [
      {
        product_id: s.product.id,
        external_lot_code: s.p + "-TWENTY",
        quantity: "20",
        total_cost: "200",
      },
    ],
  });
  return { ...s, lot: receipt.lines[0].lot_id };
}
async function producedKg(request: APIRequestContext) {
  const s = await seedTrade(request),
    producer = await api<Party>(request, "/parties", {
      name: s.p + " KURGUSAL üretici",
      roles: ["producer"],
    });
  const external = await api<Location>(request, "/locations", {
    name: s.p + " KURGUSAL dış depo",
    kind: "external_producer",
    party_id: producer.id,
  });
  const output = await api<Product>(request, "/products", {
    sku: s.p + "-REWORK-KG",
    name: s.p + " KURGUSAL kg mamul",
    type: "finished",
    base_unit: "kg",
  });
  const operation = await api<OperationDetail>(request, "/operations", {
    code: s.p + "-KG-ORIGIN",
    producer_id: producer.id,
  });
  await api(request, "/operations/" + operation.id + "/dispatch", {
    from_location_id: s.location.id,
    to_location_id: external.id,
    lines: [{ lot_id: s.lot, quantity: "10" }],
  });
  const closed = await api<OperationDetail>(
    request,
    "/operations/" + operation.id + "/post",
    {
      consumed_inputs: [
        { lot_id: s.lot, location_id: external.id, quantity: "10" },
      ],
      output_location_id: s.location.id,
      outputs: [
        {
          product_id: output.id,
          lot_code: s.p + "-SOURCE-KG",
          quantity: "10",
          unit: "kg",
        },
      ],
      service_costs: [],
      loss_quantity: "0",
    },
  );
  return { ...s, lot: closed.outputs[0].lot_id, output };
}
async function draftRework(
  page: Page,
  s: Awaited<ReturnType<typeof producedKg>>,
) {
  await page.goto("/hareketler?islem=rework");
  await page.getByLabel("Rework kodu", { exact: true }).fill(s.p + "-UI-RW");
  await page
    .getByLabel("Kaynak mamul lotu / depo", { exact: true })
    .selectOption(s.lot + "|" + s.location.id);
  await page
    .getByLabel("Rework girdi miktarı (kg)", { exact: true })
    .fill("10");
  await page
    .getByLabel("Yeniden işleme nedeni", { exact: true })
    .fill("KURGUSAL UI rework");
  await page.getByLabel(s.output.name, { exact: true }).check();
  const response = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/reworks"),
  );
  await confirm(page, "Taslağı gözden geçir");
  const record = (await (await response).json()) as Rework;
  await expect(page).toHaveURL("/hareketler/rework/" + record.id);
  return record;
}
async function fillClosing(
  page: Page,
  s: Awaited<ReturnType<typeof producedKg>>,
) {
  await page
    .getByLabel("Rework çıktı deposu", { exact: true })
    .selectOption(s.location.id);
  await page
    .getByLabel("Yeni lot kodu 1", { exact: true })
    .fill(s.p + "-RW-OUTPUT");
  await page.getByLabel("Çıktı kg 1", { exact: true }).fill("9,5");
  await page.getByLabel("Açıklanmış kayıp (kg)", { exact: true }).fill("0,5");
  await page
    .getByLabel("Kayıp nedeni", { exact: true })
    .fill("KURGUSAL fiilî ölçüm");
  await page.getByLabel("Fiilî işlem bedeli (EUR)", { exact: true }).fill("15");
  await page
    .getByLabel("Fiilî bedel belge referansı", { exact: true })
    .fill("KURGUSAL-SERVICE");
}

test("sevk satırından A→X12; gerçek kayıp cevap/reload/retry, recall toplamı85 ve bilinmeyen fiziksel stok", async ({
  page,
  request,
}) => {
  const s = await seedProduction(request),
    closed = (await closeProduction(request, s)) as OperationDetail;
  const markets = [];
  for (const [name, quantity] of [
    ["A", "30"],
    ["B", "25"],
    ["C", "30"],
  ]) {
    const customer = await api<Party>(request, "/parties", {
      name: s.p + " Market " + name + " (KURGUSAL)",
      roles: ["customer"],
    });
    const sale = await api<SaleDetail>(request, "/sales", {
      customer_id: customer.id,
      lines: [
        {
          lot_id: closed.outputs[0].lot_id,
          location_id: s.location.id,
          quantity,
          unit: "package",
          unit_price: "25",
        },
      ],
    });
    markets.push({ customer, shipment: await ship(request, sale) });
  }
  const x = await api<Party>(request, "/parties", {
    name: s.p + " Dağıtıcı X (KURGUSAL)",
    roles: ["customer"],
    contact: "x@example.invalid",
  });
  const source = markets[0].shipment.lines[0];
  await page.goto("/sevkiyatlar?shipment=" + markets[0].shipment.id);
  await page
    .getByRole("link", { name: "İkinci kademe bildirimi oluştur", exact: true })
    .click();
  await expect(
    page.getByLabel("Kaynak sevkiyat satırı", { exact: true }),
  ).toHaveValue(source.id);
  await page
    .getByLabel("İkinci kademe alıcı", { exact: true })
    .selectOption(x.id);
  await page.getByLabel("Bildirilen miktar", { exact: true }).fill("12");
  await page
    .getByLabel("Dağıtım referansı", { exact: true })
    .fill(s.p + "-SECOND-TIER");
  await page
    .getByLabel("Bildirim açıklaması", { exact: true })
    .fill("KURGUSAL operatör bildirimi");
  const attempts: Array<{ key: string | undefined; body: string | null }> = [];
  page.on("request", (r) => {
    if (
      r.method() === "POST" &&
      r.url().endsWith("/distributions/second-tier")
    ) {
      expect(r.headers()["x-api-key"]).toBeUndefined();
      attempts.push({
        key: r.headers()["idempotency-key"],
        body: r.postData(),
      });
    }
  });
  let committed: SecondTier | undefined;
  await page.route("**/api/v1/distributions/second-tier", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    committed = await response.json();
    await route.abort("failed");
  });
  await confirm(page, "Bildirimi gözden geçir");
  await expect(
    page.getByRole("button", { name: "Aynı işlemi tekrar dene", exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/v1/distributions/second-tier");
  page.once("dialog", (dialog) => dialog.accept());
  await page.reload();
  await expect(
    page.getByLabel("Bildirilen miktar", { exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Aynı işlemi tekrar dene", exact: true })
    .click();
  await expect(page).toHaveURL("/dagitimlar/" + committed!.id);
  expect(attempts).toHaveLength(2);
  expect(attempts[0]).toEqual(attempts[1]);
  const records = await api<{ items: SecondTier[] }>(
    request,
    "/distributions/second-tier?source_shipment_line_id=" + source.id,
  );
  expect(records.items).toHaveLength(1);
  expect(await stock(request, closed.outputs[0].lot_id, s.location.id)).toBe(
    "0.000000",
  );
  const recall = await api<Recall>(request, "/recalls", {
    source_lot_id: s.lots[0],
    reason: "KURGUSAL UI dağıtım recall",
  });
  await page.goto("/geri-cagirma/" + recall.id);
  await expect(page.getByText(x.name, { exact: true })).toBeVisible();
  await expect(
    page.getByText("85 paket", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByText("18 paket", { exact: true })).toBeVisible();
  await expect(
    page
      .getByText(
        "Belgelenmiş tahsis edilmemiş miktar — fiziksel stok doğrulanmadı",
      )
      .first(),
  ).toBeVisible();
  const report = (await api<Recall>(request, "/recalls/" + recall.id)).report;
  expect(report.total_shipped_quantities[0].quantity).toBe("85.000000");
  expect(report.second_tier_distributions).toHaveLength(1);
  expect(
    report.unknown_distributions.every(
      (row) =>
        row.market_remaining_quantity === null &&
        row.final_consumer_sold_quantity === null,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "/tmp/avatar-task16-recall-desktop.png",
    fullPage: true,
  });
});

test("20kg depo transferi UI→MySQL13/7; yetersiz stok reddi gerçek409", async ({
  page,
  request,
}) => {
  const s = await trade20(request),
    target = await api<Location>(request, "/locations", {
      name: s.p + " KURGUSAL B deposu",
    });
  await page.goto("/hareketler");
  await page
    .getByLabel("Kaynak lot / depo", { exact: true })
    .selectOption(s.lot + "|" + s.location.id);
  await expect(
    page
      .getByLabel("Hedef depo", { exact: true })
      .locator('option[value="' + s.location.id + '"]'),
  ).toHaveCount(0);
  await page.getByLabel("Hedef depo", { exact: true }).selectOption(target.id);
  await page.getByLabel("Transfer miktarı", { exact: true }).fill("7");
  await page
    .getByLabel("Transfer referansı", { exact: true })
    .fill(s.p + "-MOVE");
  await page
    .getByLabel("Transfer nedeni", { exact: true })
    .fill("KURGUSAL depo transferi");
  const response = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/transfers"),
  );
  await confirm(page, "Transferi gözden geçir");
  expect((await response).status()).toBe(201);
  const result = page
    .locator("section")
    .filter({
      has: page.getByRole("heading", {
        name: "Kaydedilen transfer ve güncel bakiyeler",
        exact: true,
      }),
    });
  await expect(
    result.getByRole("cell", { name: "13 kg", exact: true }),
  ).toBeVisible();
  await expect(
    result.getByRole("cell", { name: "7 kg", exact: true }),
  ).toBeVisible();
  expect(await stock(request, s.lot, s.location.id)).toBe("13.000000");
  expect(await stock(request, s.lot, target.id)).toBe("7.000000");
  await page
    .getByLabel("Kaynak lot / depo", { exact: true })
    .selectOption(s.lot + "|" + s.location.id);
  await page.getByLabel("Hedef depo", { exact: true }).selectOption(target.id);
  await page.getByLabel("Transfer miktarı", { exact: true }).fill("14");
  await page
    .getByLabel("Transfer nedeni", { exact: true })
    .fill("KURGUSAL fazla miktar");
  const rejected = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/transfers"),
  );
  await confirm(page, "Transferi gözden geçir");
  expect((await rejected).status()).toBe(409);
  await expect(page.getByRole("alert")).toContainText("yeterli stok yok");
});

test("sevke bağlı UI iadesi karantinada; satış kârlılığı backend net düzeltmesini gösterir", async ({
  page,
  request,
}) => {
  const s = await trade20(request),
    sale = await sell(request, s),
    shipment = await ship(request, sale);
  const q = await api<Location>(request, "/locations", {
    name: s.p + " KURGUSAL karantina",
    kind: "quarantine",
  });
  await page.goto("/satislar/" + sale.id);
  await expect(
    page.getByRole("heading", { name: "Satış kârlılığı", exact: true }),
  ).toBeVisible();
  const original = await api<Profitability>(
    request,
    "/sales/" + sale.id + "/profitability",
  );
  expect(original.net_revenue_eur).toBe("100.00");
  await page.getByRole("link", { name: "Müşteri iadesi", exact: true }).click();
  await page
    .getByLabel("İade sevkiyat satırı", { exact: true })
    .selectOption(shipment.lines[0].id);
  await page.getByLabel("İade miktarı", { exact: true }).fill("2");
  await page
    .getByLabel("Karantina kabul konumu", { exact: true })
    .selectOption(q.id);
  await page
    .getByLabel("İade nedeni", { exact: true })
    .fill("KURGUSAL müşteri iadesi");
  const response = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/returns"),
  );
  await confirm(page, "İadeyi gözden geçir");
  const corrected = (await (await response).json()) as Correction;
  expect(corrected.credit_amount).toBe("40.00");
  expect(corrected.restored_cost).toBe("20.000000");
  await expect(
    page.getByText("Karantina · satılabilir değil").first(),
  ).toBeVisible();
  expect(await stock(request, s.lot, q.id)).toBe("2.000000");
  const stocks = await api<{ items: Array<{ available_quantity: string }> }>(
    request,
    "/stocks?lot_id=" + s.lot + "&location_id=" + q.id,
  );
  expect(stocks.items[0].available_quantity).toBe("0.000000");
  await page
    .getByRole("link", { name: "Kaynak satış ve net kârlılık", exact: true })
    .click();
  await expect(page.getByText("Kısmi iade", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "İade / iptal sonrası netleşmiş sonuç",
      exact: true,
    }),
  ).toBeVisible();
  const profit = await api<Profitability>(
    request,
    "/sales/" + sale.id + "/profitability",
  );
  expect(profit.net_after_adjustments.net_revenue_eur).toBe("60.00");
  expect(profit.net_after_adjustments.recognized_cost_eur).toBe("30.000000");
  await expect(page.getByText("60,00 €", { exact: true })).toBeVisible();
  await expect(
    page.getByText(
      "Vergi, indirim ve genel gider bu ekranda hesaplanmaz. Gösterimden yeniden maliyet türetilmez.",
    ),
  ).not.toBeVisible();
});

test("sevk yarışı sonrası iptal backend tarafından reddedilir; uygun satış iki onayla iptal edilir", async ({
  page,
  request,
}) => {
  const s = await trade20(request),
    sale = await sell(request, s, "3");
  const q = await api<Location>(request, "/locations", {
    name: s.p + " KURGUSAL iptal karantina",
    kind: "quarantine",
  });
  async function fill(saleId: string) {
    await page.goto("/hareketler?islem=iptal&sale=" + saleId);
    await page
      .getByLabel("İptal karantina konumu", { exact: true })
      .selectOption(q.id);
    await page
      .getByLabel("İptal nedeni", { exact: true })
      .fill("KURGUSAL satış iptali");
    await page
      .getByLabel(
        "Tam satışın iptal edileceğini ve ürünün karantinaya alınacağını anladım.",
        { exact: true },
      )
      .check();
  }
  await fill(sale.id);
  await ship(request, sale);
  const rejected = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/cancel"),
  );
  await confirm(page, "İptali gözden geçir");
  expect((await rejected).status()).toBe(409);
  await expect(page.getByRole("alert")).toContainText("Bu satış sevk edilmiş");
  const next = await sell(request, s, "2");
  await fill(next.id);
  const response = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/cancel"),
  );
  await confirm(page, "İptali gözden geçir");
  expect((await response).status()).toBe(200);
  const result = (await (await response).json()) as Correction;
  await expect(
    page.getByRole("heading", { name: "Kesin düzeltme kaydı", exact: true }),
  ).toBeVisible();
  expect(
    (await api<Correction>(request, "/sales/" + next.id + "/cancellation")).id,
  ).toBe(result.id);
  expect((await api<SaleDetail>(request, "/sales/" + next.id)).lines).toEqual(
    next.lines,
  );
});

test("rework taslağı stok tüketmez; kapanış kayıp cevabı posted sonrası reload ile aynı key/body tek yeni lot115EUR", async ({
  page,
  request,
}) => {
  const s = await producedKg(request),
    draft = await draftRework(page, s);
  expect(draft.status).toBe("draft");
  expect(await stock(request, s.lot, s.location.id)).toBe("10.000000");
  await expect(
    page.getByRole("heading", { name: "Rework kesin kapanışı", exact: true }),
  ).toBeVisible();
  await fillClosing(page, s);
  const attempts: Array<{ key: string | undefined; body: string | null }> = [];
  let committed: Rework | undefined;
  page.on("request", (r) => {
    if (
      r.method() === "POST" &&
      r.url().endsWith("/reworks/" + draft.id + "/post")
    )
      attempts.push({
        key: r.headers()["idempotency-key"],
        body: r.postData(),
      });
  });
  await page.route("**/api/v1/reworks/" + draft.id + "/post", async (route) => {
    const response = await route.fetch();
    expect(response.status()).toBe(200);
    committed = await response.json();
    await route.abort("failed");
  });
  await confirm(page, "Kesin kapanışı gözden geçir");
  await expect(
    page.getByRole("button", { name: "Aynı işlemi tekrar dene", exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/v1/reworks/" + draft.id + "/post");
  page.once("dialog", (dialog) => dialog.accept());
  await page.reload();
  await page
    .getByRole("button", { name: "Aynı işlemi tekrar dene", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Kesin rework çıktıları", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: "Kesin kapanışı gözden geçir",
      exact: true,
    }),
  ).toHaveCount(0);
  expect(attempts).toHaveLength(2);
  expect(attempts[0]).toEqual(attempts[1]);
  const closed = await api<Rework>(request, "/reworks/" + draft.id);
  expect(closed.outputs).toHaveLength(1);
  expect(closed.outputs[0].lot_id).toBe(committed!.outputs[0].lot_id);
  expect(closed.total_material_cost).toBe("100.000000");
  expect(closed.total_service_cost).toBe("15.000000");
  expect(closed.total_cost).toBe("115.000000");
  expect(await stock(request, s.lot, s.location.id)).toBe("0.000000");
  expect(await stock(request, closed.outputs[0].lot_id, s.location.id)).toBe(
    "9.500000",
  );
  await page
    .getByRole("link", { name: s.p + "-RW-OUTPUT", exact: false })
    .click();
  await expect(page).toHaveURL(/izlenebilirlik\?lot=/);
});

test("taslak sonrası kaynak recall olursa rework kapanışı gerçek LOT_BLOCKED ile reddedilir", async ({
  page,
  request,
}) => {
  const s = await producedKg(request),
    draft = await draftRework(page, s);
  await fillClosing(page, s);
  await api(request, "/recalls", {
    source_lot_id: s.lot,
    reason: "KURGUSAL kapanış yarışı",
  });
  const response = page.waitForResponse(
    (r) =>
      r.request().method() === "POST" &&
      r.url().endsWith("/reworks/" + draft.id + "/post"),
  );
  await confirm(page, "Kesin kapanışı gözden geçir");
  expect((await response).status()).toBe(409);
  await expect(page.getByRole("alert")).toContainText("bloke");
  expect(
    (await api<Rework>(request, "/reworks/" + draft.id)).outputs,
  ).toHaveLength(0);
});

for (const width of [390, 768, 1440])
  test(
    "operasyon ekranları " +
      width +
      "px: klavye etiketleri, gerçek kayıtlar ve sayfa taşması",
    async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      for (const path of [
        "/dagitimlar",
        "/hareketler",
        "/hareketler?islem=iade",
        "/hareketler?islem=rework",
      ]) {
        await page.goto(path);
        await expect(page.locator("main h2").first()).toBeVisible();
        await expect(
          page.getByText("Kayıtlar yükleniyor…", { exact: true }),
        ).toHaveCount(0);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth + 1,
          ),
        ).toBe(true);
        await page.keyboard.press("Tab");
      }
      await page.screenshot({
        path: "/tmp/avatar-task16-operations-" + width + ".png",
        fullPage: true,
      });
    },
  );

test("iptal commit cevabı kaybolup sayfa yenilenince aynı iptal güvenle tekrarlanır", async ({
  page,
  request,
}) => {
  const s = await trade20(request),
    sale = await sell(request, s, "2"),
    q = await api<Location>(request, "/locations", {
      name: s.p + " KURGUSAL tekrar karantina",
      kind: "quarantine",
    });
  await page.goto("/hareketler?islem=iptal&sale=" + sale.id);
  await page
    .getByLabel("İptal karantina konumu", { exact: true })
    .selectOption(q.id);
  await page
    .getByLabel("İptal nedeni", { exact: true })
    .fill("KURGUSAL kayıp cevap");
  await page
    .getByLabel(
      "Tam satışın iptal edileceğini ve ürünün karantinaya alınacağını anladım.",
      { exact: true },
    )
    .check();
  const attempts: Array<{ key: string | undefined; body: string | null }> = [];
  let committed: Correction | undefined;
  page.on("request", (r) => {
    if (
      r.method() === "POST" &&
      r.url().endsWith("/sales/" + sale.id + "/cancel")
    )
      attempts.push({
        key: r.headers()["idempotency-key"],
        body: r.postData(),
      });
  });
  await page.route("**/api/v1/sales/" + sale.id + "/cancel", async (route) => {
    const response = await route.fetch();
    expect(response.status()).toBe(200);
    committed = await response.json();
    await route.abort("failed");
  });
  await confirm(page, "İptali gözden geçir");
  await expect(
    page.getByRole("button", { name: "Aynı işlemi tekrar dene", exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/v1/sales/" + sale.id + "/cancel");
  page.once("dialog", (dialog) => dialog.accept());
  await page.reload();
  await page
    .getByRole("button", { name: "Aynı işlemi tekrar dene", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Kesin düzeltme kaydı", exact: true }),
  ).toBeVisible();
  expect(attempts).toHaveLength(2);
  expect(attempts[0]).toEqual(attempts[1]);
  expect(
    (await api<Correction>(request, "/sales/" + sale.id + "/cancellation")).id,
  ).toBe(committed!.id);
  expect(await stock(request, s.lot, q.id)).toBe("2.000000");
});

test("yeni operasyon formları mobil/masaüstü otomatik erişilebilirlik kontrolü", async ({
  page,
}) => {
  const { default: AxeBuilder } = await import("@axe-core/playwright");
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of [
      "/dagitimlar",
      "/hareketler",
      "/hareketler?islem=iade",
      "/hareketler?islem=iptal",
      "/hareketler?islem=rework",
    ]) {
      await page.goto(path);
      await expect(
        page.getByText("Kayıtlar yükleniyor…", { exact: true }),
      ).toHaveCount(0);
      const result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(
        result.violations.map((item) => ({
          id: item.id,
          impact: item.impact,
          targets: item.nodes.map((node) => node.target),
        })),
      ).toEqual([]);
    }
  }
});
