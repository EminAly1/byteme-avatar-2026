import { test, expect } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

test("390px: örnekler değer değildir, virgüllü giriş ve mobil menü korunur", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const errors: string[] = [], writes: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => {
    if (request.url().includes("/api/") && !["GET", "HEAD"].includes(request.method())) writes.push(request.method());
  });
  const artifacts = process.env.AVATAR_E2E_ARTIFACT_DIR || "test-results/final-polish";
  mkdirSync(artifacts, { recursive: true });
  const rows = [];
  for (const route of ["/urunler", "/is-ortaklari", "/depolar", "/alislar", "/uretim", "/parcalama", "/hareketler", "/satislar", "/yapay-zeka", "/geri-cagirma", "/uyarilar"]) {
    await page.goto(route);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.locator(".loading-state")).toHaveCount(0);
    if (route === "/urunler") {
      await page.getByRole("button", { name: "Ürün ekle", exact: true }).click();
      await expect(page.getByLabel("SKU", { exact: true })).toHaveValue("");
      await expect(page.getByLabel("Ürün adı", { exact: true })).toHaveValue("");
      await page.getByLabel("Stok birimi", { exact: true }).selectOption("package");
      const weight = page.getByLabel("Bir paket kaç kg?", { exact: true });
      await expect(weight).toHaveValue("");
      await expect(weight).toHaveAttribute("inputmode", "decimal");
      await weight.fill("0,5");
      await expect(weight).toHaveValue("0,5");
      const contrast = await weight.evaluate(input => {
        const rgb = (color: string) => color.match(/[\d.]+/g)!.slice(0, 3).map(Number).map(x => {
          x /= 255; return x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4;
        });
        const luminance = (color: string) => rgb(color).reduce((sum, x, i) => sum + x * [.2126, .7152, .0722][i], 0);
        const a = luminance(getComputedStyle(input, "::placeholder").color), b = luminance(getComputedStyle(input).backgroundColor);
        return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
      });
      expect(contrast).toBeGreaterThanOrEqual(4.5);
      await page.getByRole("button", { name: "Ürünü oluştur", exact: true }).click();
      await expect(page.getByLabel("SKU", { exact: true })).toHaveAttribute("aria-invalid", "true");
      await page.screenshot({ path: join(artifacts, "products-390.png"), fullPage: true, animations: "disabled" });
    }
    if (route === "/alislar") {
      await expect(page.getByLabel("Lot numarası 1", { exact: true })).toHaveValue("");
      await page.getByLabel("Miktar 1", { exact: true }).fill("0,000001");
      await page.getByLabel("Toplam maliyet 1 (EUR)", { exact: true }).fill("18,16");
      await expect(page.getByLabel("Miktar 1", { exact: true })).toHaveValue("0,000001");
      await expect(page.getByLabel("Toplam maliyet 1 (EUR)", { exact: true })).toHaveValue("18,16");
    }
    if (route === "/yapay-zeka") {
      await expect(page.getByLabel("Planlanan et (kg)", { exact: true })).toHaveValue("");
      await expect(page.getByLabel("Planlanan et (kg)", { exact: true })).toHaveAttribute("placeholder", "Örn: 25");
    }
    if (route === "/geri-cagirma") {
      const lookup = page.getByLabel("Geri çağırma kayıt kimliği", { exact: true });
      await lookup.fill("eksik");
      await page.getByRole("button", { name: "Kaydı aç", exact: true }).click();
      await expect(lookup).toHaveAttribute("aria-invalid", "true");
      await expect(lookup).toHaveAccessibleDescription(/Geçerli bir geri çağırma kayıt kimliği girin/);
    }
    if (route === "/uyarilar") {
      await page.getByText("Kaynak lot veya işlem filtresi", { exact: true }).click();
      await page.getByLabel("Kaynak kayıt kimliği", { exact: false }).fill("eksik");
      await page.getByRole("button", { name: "Kaynağa göre filtrele", exact: true }).click();
      await expect(page.locator('input[aria-invalid="true"]')).toHaveAccessibleDescription(/tam kayıt kimliğini/);
    }
    const row = await page.locator("main").evaluate(main => ({
      overflow: document.documentElement.scrollWidth > innerWidth + 1,
      inputs: Array.from(main.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>('input:not([type="checkbox"]):not([type="radio"]):not([type="date"]):not([type="datetime-local"]),textarea'))
        .map(input => ({ name: input.name || input.id, placeholder: input.placeholder })),
    }));
    expect(row.overflow, route).toBe(false);
    expect(row.inputs.filter(input => !input.placeholder.startsWith("Örn: ")), route).toEqual([]);
    rows.push({ route, ...row });
  }
  const open = page.getByRole("button", { name: "Menüyü aç", exact: true });
  await open.click();
  await expect(page.getByRole("button", { name: "Menüyü kapat", exact: true })).toBeFocused();
  expect(await page.evaluate(() => document.body.style.overflow)).toBe("hidden");
  await page.screenshot({ path: join(artifacts, "menu-390.png"), animations: "disabled" });
  await page.keyboard.press("Escape");
  await expect(open).toBeFocused();
  await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");
  await expect(page.locator("footer")).toHaveText(/AVATAR/);
  await expect(page.locator("footer")).not.toContainText("AVATAR 2026");
  expect(errors).toEqual([]);
  expect(writes).toEqual([]);
  writeFileSync(join(artifacts, "inputs-390.json"), JSON.stringify({ rows, writes, errors }, null, 2));
});
