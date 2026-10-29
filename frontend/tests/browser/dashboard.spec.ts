import { test, expect, type Page } from "@playwright/test";

const prefix = "WEB-" + Date.now();
async function confirm(page: Page, label: string) {
  await page.getByRole("button", { name: label, exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("button", { name: "Onayla ve kaydet", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
}
async function location(
  page: Page,
  name: string,
  kind = "warehouse",
  producer?: string,
) {
  await page.goto("/depolar");
  await page.getByLabel("Depo / konum adı", { exact: true }).fill(name);
  await page.getByLabel("Konum türü", { exact: true }).selectOption(kind);
  if (producer)
    await page
      .getByLabel("İlgili dış üretici", { exact: true })
      .selectOption({ label: producer });
  await confirm(page, "Konumu oluştur");
  await expect(page.getByRole("cell", { name, exact: true })).toBeVisible();
}
async function product(
  page: Page,
  sku: string,
  name: string,
  type = "raw",
  unit = "kg",
) {
  await page.goto("/urunler");
  await page.getByRole("button", { name: "Ürün ekle", exact: true }).click();
  await page.getByLabel("SKU", { exact: true }).fill(sku);
  await page.getByLabel("Ürün adı", { exact: true }).fill(name);
  await page.getByLabel("Ürün türü", { exact: true }).selectOption(type);
  await page.getByLabel("Stok birimi", { exact: true }).selectOption(unit);
  if (unit === "package")
    await page.getByLabel("Bir paket kaç kg?", { exact: true }).fill("1");
  await confirm(page, "Ürünü oluştur");
  await expect(
    page.getByRole("cell", { name: sku, exact: true }),
  ).toBeVisible();
}

test("gerçek UI: çok satırlı alış → sevk → üretim kapanışı → doğru EKP ve stok", async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  page.on("pageerror", (e) => consoleErrors.push(e.message));
  page.on("request", (req) => {
    if (req.url().includes("/api/"))
      expect("x-api-key" in req.headers()).toBe(false);
  });
  const supplier = prefix + " Tedarikçi",
    producer = prefix + " Üretici",
    warehouse = prefix + " Merkez",
    external = prefix + " Üretici konumu";
  await page.goto("/is-ortaklari");
  await page.getByLabel("Firma adı", { exact: true }).fill(supplier);
  await confirm(page, "Firmayı oluştur");
  await expect(
    page.getByRole("cell", { name: supplier, exact: true }),
  ).toBeVisible();
  await page.getByLabel("Firma adı", { exact: true }).fill(producer);
  await page.getByLabel("Tedarikçi", { exact: true }).uncheck();
  await page.getByLabel("Dış üretici", { exact: true }).check();
  await confirm(page, "Firmayı oluştur");
  await expect(
    page.getByRole("cell", { name: producer, exact: true }),
  ).toBeVisible();
  await location(page, warehouse);
  await location(page, external, "external_producer", producer);
  const names = [prefix + " Et", prefix + " Baharat", prefix + " Bağırsak"],
    skus = ["ET", "BAH", "BAG"].map((x) => prefix + "-" + x);
  for (let i = 0; i < 3; i++) await product(page, skus[i], names[i]);
  const finished = prefix + " Sucuk";
  await product(page, prefix + "-SUC", finished, "finished", "package");
  await page.goto("/alislar");
  await page
    .getByLabel("Tedarikçi", { exact: true })
    .selectOption({ label: supplier });
  await page
    .getByLabel("Kabul deposu", { exact: true })
    .selectOption({ label: warehouse });
  await page
    .getByLabel("Belge / alış referansı", { exact: true })
    .fill(prefix + "-ALIS");
  const quantities = ["100", "2", "5"],
    costs = ["970,00", "48,00", "58,00"],
    lots = ["ET", "BAH", "BAG"].map((x) => prefix + "-" + x + "-001");
  for (let i = 0; i < 3; i++) {
    if (i)
      await page
        .getByRole("button", { name: "Alış satırı ekle", exact: true })
        .click();
    await page
      .getByLabel(`Ürün ${i + 1}`, { exact: true })
      .selectOption({ label: `${skus[i]} · ${names[i]} (kg)` });
    await page
      .getByLabel(`Lot numarası ${i + 1}`, { exact: true })
      .fill(lots[i]);
    await page
      .getByLabel(`Miktar ${i + 1}`, { exact: true })
      .fill(quantities[i]);
    await page
      .getByLabel(`Toplam maliyet ${i + 1} (EUR)`, { exact: true })
      .fill(costs[i]);
  }
  const receiptRequest = page.waitForRequest(
    (r) => r.method() === "POST" && r.url().endsWith("/api/v1/receipts"),
  );
  await confirm(page, "Alışı kaydet");
  const sent = (await receiptRequest).postDataJSON();
  expect(sent.lines).toHaveLength(3);
  expect(sent.lines[0].total_cost).toBe("970.00");
  expect(typeof sent.lines[0].quantity).toBe("string");
  await expect(
    page.getByText("Alış kaydedildi. Lotlar ve stok hareketleri oluşturuldu.", {
      exact: true,
    }),
  ).toBeVisible();
  for (const lot of lots)
    await expect(
      page.getByRole("cell", { name: lot, exact: true }),
    ).toBeVisible();
  await page.goto("/uretim");
  await page
    .getByLabel("Üretim emri numarası", { exact: true })
    .fill(prefix + "-URT");
  await page
    .getByLabel("Dış üretici", { exact: true })
    .selectOption({ label: producer });
  await confirm(page, "Emri oluştur");
  await expect(page).toHaveURL(/\/uretim\/[0-9a-f-]+/);
  const operationUrl = page.url();
  await page
    .getByLabel("Sevk çıkış deposu", { exact: true })
    .selectOption({ label: warehouse });
  await page
    .getByLabel("Üretici kabul konumu", { exact: true })
    .selectOption({ label: external });
  for (let i = 0; i < 3; i++) {
    if (i)
      await page
        .getByRole("button", { name: "Sevk satırı ekle", exact: true })
        .click();
    const option = page
      .getByLabel(`Sevk lotu ${i + 1}`, { exact: true })
      .locator("option")
      .filter({ hasText: lots[i] });
    await page
      .getByLabel(`Sevk lotu ${i + 1}`, { exact: true })
      .selectOption((await option.getAttribute("value"))!);
    await page
      .getByLabel(`Sevk miktarı ${i + 1}`, { exact: true })
      .fill(quantities[i]);
  }
  await confirm(page, "Hammadde sevkini kaydet");
  await expect(
    page.getByRole("heading", {
      name: "Mamul kabulü ve üretim kapanışı",
      exact: true,
    }),
  ).toBeVisible();
  for (let i = 0; i < 3; i++) {
    if (i)
      await page
        .getByRole("button", { name: "Tüketim satırı ekle", exact: true })
        .click();
    const select = page.getByLabel(`Tüketilen lot / konum ${i + 1}`, {
      exact: true,
    });
    const value = await select
      .locator("option")
      .filter({ hasText: lots[i] })
      .getAttribute("value");
    await select.selectOption(value!);
    await page
      .getByLabel(`Fiilî tüketim ${i + 1}`, { exact: true })
      .fill(quantities[i]);
  }
  await page
    .getByLabel("Mamul kabul deposu", { exact: true })
    .selectOption({ label: warehouse });
  await page
    .getByLabel("Mamul ürün 1", { exact: true })
    .selectOption({ label: finished + " (paket)" });
  await page
    .getByLabel("Mamul lot numarası 1", { exact: true })
    .fill(prefix + "-SUC-045");
  await page.getByLabel("Mamul miktarı 1", { exact: true }).fill("85");
  await page
    .getByLabel("Toplam hizmet bedeli (EUR)", { exact: true })
    .fill("467,50");
  await page.getByLabel("Miktar farkı / fire (kg)", { exact: true }).fill("22");
  await page
    .getByLabel("Miktar farkı açıklaması", { exact: true })
    .fill("Tarayıcı testi: kayıtlı üretim farkı");
  await confirm(page, "Üretimi kapat");
  await expect(
    page.getByRole("heading", { name: "Mamul kabulü ve EKP", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "1.543,50 €", exact: true }),
  ).toBeVisible();
  await expect(
    page
      .locator(".stat")
      .filter({ hasText: "Gerçek toplam maliyet" })
      .getByText("1.543,50 €", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "18,16 €", exact: true }),
  ).toBeVisible();
  for (const lot of lots)
    await expect(
      page.getByRole("cell", { name: lot, exact: true }),
    ).toBeVisible();
  await page.screenshot({
    path: "test-results/production-desktop.png",
    fullPage: true,
  });
  await page.goto("/stoklar");
  await page
    .getByLabel("Ürün", { exact: true })
    .selectOption({ label: finished });
  const row = page.getByRole("row").filter({ hasText: prefix + "-SUC-045" });
  await expect(
    row.getByRole("cell", { name: "85 paket", exact: true }),
  ).toHaveCount(2);
  await page
    .getByRole("button", { name: "Hareket geçmişi", exact: true })
    .click();
  await expect(
    page.getByRole("cell", { name: "Mamul kabulü", exact: true }),
  ).toBeVisible();
  await page.goto(operationUrl);
  await expect(
    page.getByRole("cell", { name: "18,16 €", exact: true }),
  ).toBeVisible();
  expect(consoleErrors).toEqual([]);
});

test("belgedeki mevcut demo gerçek API kaydından gösterilir", async ({
  page,
}) => {
  await page.goto("/uretim");
  const row = page.getByRole("row").filter({ hasText: "URT-2026-045" });
  await row.getByRole("link", { name: "Emri aç" }).click();
  await expect(
    page.getByRole("cell", { name: "SUC-2026-045", exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "ET-2026-001", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "18,16 €", exact: true }),
  ).toBeVisible();
});

test("tablet ve mobil yerleşim; recall onay verilmeden işlem başlatmaz", async ({
  page,
}) => {
  await page.setViewportSize({ width: 834, height: 1112 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Operasyon özeti/ }),
  ).toBeVisible();
  await expect(page.getByText("Veriler alınamadı.")).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/dashboard-tablet.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Menüyü aç", exact: true }).click();
  await page.locator('.sidebar').getByRole('button',{name:'İzlenebilirlik ve Güvenlik',exact:true}).click();
  await page.getByRole("link", { name: "Geri çağırma", exact: true }).click();
  await expect(
    page.getByLabel("Sorunlu kaynak lot", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Geri çağırmayı gözden geçir", exact: true }),
  ).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/recall-mobile.png",
    fullPage: true,
  });
});

test("yerel proxy uzak origin/host ve originsiz yazmayı reddeder; gizli dosya servis edilmez", async ({
  request,
}) => {
  expect(
    (
      await request.get("/api/v1/products", {
        headers: { Origin: "https://evil.example" },
      })
    ).status(),
  ).toBe(403);
  expect(
    (
      await request.get("/api/v1/products", {
        headers: { Host: "evil.example" },
      })
    ).status(),
  ).toBe(403);
  expect((await request.post("/api/v1/products", { data: {} })).status()).toBe(
    403,
  );
  expect(
    (
      await request.get(
        "/@fs/workspace/byteme-avatar-2026/backend/.env.runtime",
      )
    ).status(),
  ).toBe(403);
  expect((await request.get("/api/v1/products")).status()).toBe(200);
  const secret = process.env.AVATAR_API_KEY;
  if (!secret)
    throw new Error(
      "Secret sızıntı testi için AVATAR_API_KEY yalnızca test Node process ortamına verilmeli.",
    );
  for (const path of ["/", "/@vite/env", "/src/main.tsx"]) {
    const response = await request.get(path);
    expect((await response.text()).includes(secret)).toBe(false);
  }
});
