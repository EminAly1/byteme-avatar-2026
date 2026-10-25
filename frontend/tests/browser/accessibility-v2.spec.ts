import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir, writeFile } from "node:fs/promises";
test("WCAG AA otomatik kontrast, etiket ve yapı denetimi: desktop/mobil ana ekranlar", async ({
  page,
}) => {
  test.setTimeout(120000);
  const evidence = [];
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of [
      "/",
      "/parcalama",
      "/satislar",
      "/izlenebilirlik",
      "/geri-cagirma",
      "/yapay-zeka",
      "/urunler",
      "/alislar",
      "/uretim",
    ]) {
      await page.goto(route);
      await expect(page.getByText("Kayıtlar yükleniyor…")).toHaveCount(0, {
        timeout: 20000,
      });
      await expect(page.getByRole("alert")).toHaveCount(0);
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      evidence.push({
        width,
        route,
        violations: results.violations.map((v) => ({
          id: v.id,
          impact: v.impact,
          nodes: v.nodes.map((n) => ({
            target: n.target,
            summary: n.failureSummary,
          })),
        })),
      });
    }
  }
  await mkdir("validation-v2", { recursive: true });
  await writeFile(
    "validation-v2/accessibility.json",
    JSON.stringify(evidence, null, 2) + "\n",
  );
  expect(
    evidence.filter((x) => x.violations.length),
    JSON.stringify(
      evidence.filter((x) => x.violations.length),
      null,
      2,
    ),
  ).toEqual([]);
});
