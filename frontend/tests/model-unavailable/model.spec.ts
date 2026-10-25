import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
test("gerçek eksik-model backend 503: hata görünür, sahte tahmin/metrik yok", async ({
  page,
}) => {
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/v1/predictions/models"),
  );
  await page.goto("/yapay-zeka");
  expect((await response).status()).toBe(503);
  await expect(page.getByRole("alert")).toContainText("Tahmin üretilmedi");
  await expect(
    page.getByRole("button", {
      name: "Üretim tahminini gözden geçir",
      exact: true,
    }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Üretim tahmin sonucu", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("heading", {
      name: "Sentetik test metrikleri",
      exact: true,
    }),
  ).toHaveCount(0);
  await expect(page.getByText('Kayıtlar alınıyor', {exact:true})).toHaveCount(0, {timeout:20000});
  await mkdir("validation-v2/screenshots", { recursive: true });
  await page.screenshot({
    path: "validation-v2/screenshots/model-unavailable-desktop.png",
    fullPage: true,
  });
});
