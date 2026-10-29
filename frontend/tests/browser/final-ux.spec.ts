import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { navigation } from "../../src/lib/navigation";
const root = process.env.AVATAR_FINAL_UX_SEED_DIR;
if (!root)
  throw new Error(
    "AVATAR_FINAL_UX_SEED_DIR gerekli: verify_release_demo + demo_documents/rework/second_tier çıktıları; yalnız izole *_test DB.",
  );
const load = (name: string) =>
  JSON.parse(readFileSync(join(root, name + ".json"), "utf8"));
const core = load("core-seed"),
  docs = load("documents-seed"),
  rw = load("rework").flow,
  second = load("second-tier").flow;
const routes = [
  ...new Set(navigation.flatMap((g) => g.items.map((x) => x.path))),
  "/uretim/" + core.production.operation_id,
  "/parcalama/" + Object.values(core.cutting.operation_ids)[0],
  "/satislar/" + docs.active_sale_id,
  "/dagitimlar/" + second.distribution_id,
  "/hareketler/rework/" + rw.rework_id,
  "/geri-cagirma/" + core.recall.recall_id,
  "/izlenebilirlik?lot=" + second.root_lot_id,
  "/yapay-zeka?prediction=" + core.predictions.production.id,
  "/belgeler/satis/" + docs.active_sale_id,
  "/belgeler/satis/" + docs.active_sale_id + "/duzenle",
  "/belgeler/satis/" + docs.long_sale_id,
];
const artifacts = process.env.AVATAR_E2E_ARTIFACT_DIR || "validation-final-ux";
for (const width of [360, 390, 768, 1024, 1440])
  test(`${width}px: tüm iş rotaları, gerçek API, konsol, taşma, dokunma ve erişilebilirlik`, async ({
    page,
  }) => {
    test.setTimeout(240000);
    mkdirSync(artifacts, { recursive: true });
    const rows = [];
    for (const [index, route] of routes.entries()) {
      const errors: string[] = [];
      const onError = (e: Error) => errors.push(e.message);
      const onConsole = (m: { type: () => string; text: () => string }) => {
        if (m.type() === "error") errors.push(m.text());
      };
      page.on("pageerror", onError);
      page.on("console", onConsole);
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(route);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.locator(".loading-state")).toHaveCount(0, {
        timeout: 30000,
      });
      const audit = await page.evaluate(() => ({
        title: document.querySelector("h1")?.textContent,
        description: document.querySelector(".page-description")?.textContent,
        overflow: document.documentElement.scrollWidth > innerWidth + 1,
        alerts: [...document.querySelectorAll('[role="alert"]')].map(
          (e) => e.textContent,
        ),
        smallTargets: [
          ...document.querySelectorAll(
            "main button,main .button,main .text-button,main .tabs a",
          ),
        ].flatMap((e) => {
          const r = e.getBoundingClientRect();
          return r.width &&
            r.height &&
            e.checkVisibility() &&
            (r.width < 43.9 || r.height < 43.9)
            ? [
                {
                  text: e.textContent?.trim(),
                  width: r.width,
                  height: r.height,
                },
              ]
            : [];
        }),
      }));
      const axe = [390, 1440].includes(width)
        ? (
            await new AxeBuilder({ page })
              .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
              .analyze()
          ).violations.map((v) => ({
            id: v.id,
            impact: v.impact,
            targets: v.nodes.map((n) => n.target),
          }))
        : [];
      const screenshot = `route-${String(index + 1).padStart(2, "0")}-${width}.png`;
      await page.screenshot({
        path: join(artifacts, screenshot),
        fullPage: true,
        animations: "disabled",
      });
      rows.push({ route, width, screenshot, errors, ...audit, axe });
      page.off("pageerror", onError);
      page.off("console", onConsole);
    }
    writeFileSync(
      join(artifacts, `routes-${width}.json`),
      JSON.stringify(rows, null, 2),
    );
    expect(
      rows.filter(
        (r) =>
          r.overflow ||
          r.errors.length ||
          r.alerts.length ||
          r.smallTargets.length ||
          r.axe.length ||
          !r.description,
      ),
    ).toEqual([]);
  });
test("mobil menü: yedi grup, bütün bağlantılar, arka plan kilidi ve odak", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/");
  await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");
  const open = page.getByRole("button", { name: "Menüyü aç", exact: true });
  await open.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: "Menüyü kapat", exact: true }),
  ).toBeFocused();
  expect(await page.evaluate(() => document.body.style.overflow)).toBe(
    "hidden",
  );
  await page.keyboard.press("Shift+Tab");
  await expect(page.locator(".sidebar .brand")).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(
    page
      .locator(".sidebar")
      .getByRole("button", { name: "Belgeler", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator(".sidebar .brand")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(open).toBeFocused();
  for (const group of navigation)
    for (const item of group.items) {
      await open.click();
      const toggle = page
        .locator(".sidebar")
        .getByRole("button", { name: group.label, exact: true });
      if ((await toggle.getAttribute("aria-expanded")) === "false")
        await toggle.click();
      await page
        .locator(".sidebar")
        .locator("a")
        .filter({ hasText: item.label })
        .click();
      await expect(page).toHaveURL(item.path);
      await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");
      expect(await page.evaluate(() => document.body.style.overflow)).not.toBe(
        "hidden",
      );
    }
});
test("390px belge: ayrı taslak, satır doğrulama, çok sayfalı PDF modalı ve klavye", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 900 });
  const writes: string[] = [];
  page.on("request", (r) => {
    if (
      ["POST", "PATCH", "DELETE", "PUT"].includes(r.method()) &&
      r.url().includes("/api/v1/") &&
      !r.url().endsWith("/document-drafts/proforma/pdf")
    )
      writes.push(r.url());
  });
  await page.goto("/belgeler/satis/" + docs.long_sale_id);
  await expect(page.locator("main input,main textarea")).toHaveCount(0);
  await page.getByRole("link", { name: "Taslak düzenle", exact: true }).click();
  const note = page.getByLabel(/^Özel not/);
  await note.fill(Array(22).fill("satır").join("\n"));
  await page
    .getByRole("button", { name: "Değişiklikleri bu görünümde uygula" })
    .click();
  expect(
    await note.evaluate((e) => (e as HTMLTextAreaElement).validationMessage),
  ).toContain("21 satır");
  await expect(page).toHaveURL(/duzenle$/);
  await note.fill("Türkçe: ğ ü ş ı İ ö ç");
  await page
    .getByRole("button", { name: "Değişiklikleri bu görünümde uygula" })
    .click();
  await expect(
    page.getByRole("article", { name: "A4 belge önizlemesi" }),
  ).toContainText("Türkçe: ğ ü ş ı İ ö ç");
  const preview = page.getByRole("button", { name: "Önizle", exact: true });
  await preview.click();
  const dialog = page.getByRole("dialog", { name: "Belge önizleme" });
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Önizlemeyi kapat" }),
  ).toBeFocused();
  await expect(dialog.getByText(/sayfalı PDF hazır/)).toBeVisible({
    timeout: 60000,
  });
  expect(await dialog.locator("canvas").count()).toBeGreaterThan(1);
  await page.screenshot({ path: join(artifacts, "pdf-preview-390.png") });
  await page.keyboard.press("Shift+Tab");
  expect(
    await page.evaluate(() =>
      document.activeElement?.getAttribute("aria-label"),
    ),
  ).toBe("Kaydırılabilir belge");
  await page.keyboard.press("Tab");
  await expect(
    dialog.getByRole("button", { name: "Önizlemeyi kapat" }),
  ).toBeFocused();
  await dialog.getByRole("button", { name: "Yakınlaştır" }).click();
  await expect(dialog.getByText("%125")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await dialog.getByRole("button", { name: "Metin görünümü" }).click();
  await expect(dialog.getByRole("article")).toContainText(
    "Türkçe: ğ ü ş ı İ ö ç",
  );
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(preview).toBeFocused();
  expect(await page.evaluate(() => document.body.style.overflow)).not.toBe(
    "hidden",
  );
  for (const width of [768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await preview.click();
    await expect(dialog.getByText(/sayfalı PDF hazır/)).toBeVisible({
      timeout: 60000,
    });
    const bounds = await dialog.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.x).toBeCloseTo((width - bounds!.width) / 2, 0);
    expect(bounds!.y).toBeCloseTo((1000 - bounds!.height) / 2, 0);
    expect(await dialog.locator("canvas").count()).toBeGreaterThan(1);
    await page.screenshot({
      path: join(artifacts, `pdf-preview-${width}.png`),
    });
    await page.keyboard.press("Escape");
    await expect(preview).toBeFocused();
  }
  expect(writes).toEqual([]);
});
