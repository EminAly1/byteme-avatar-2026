// Read-only browser evidence. Run against the guarded Vite proxy and an isolated
// fixture described by visual-reference.json; never points at a production DB.
import { chromium } from "playwright-core";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL(".", import.meta.url));
const refs = JSON.parse(
  await fs.readFile(root + "visual-reference.json", "utf8"),
);
const base = process.env.AVATAR_UI_URL || "http://127.0.0.1:5173";
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
  args: ["--no-sandbox"],
});
const context = await browser.newContext();
const page = await context.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
await page.route("**/api/**", (route) =>
  ["GET", "HEAD", "OPTIONS"].includes(route.request().method())
    ? route.continue()
    : route.abort(),
);
try {
  const selectors = {
    dashboard: ".overview-heading",
    cutting: ".detail-heading",
    sale: ".detail-heading",
    trace: ".trace-flow",
    recall: ".recall-banner",
    "ai-production": ".prediction-main",
    "ai-cutting": ".prediction-main",
  };
  const viewports = [
    { name: "narrow", width: 360, height: 800 },
    { name: "mobile", width: 390, height: 844 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "landscape", width: 1024, height: 768 },
    { name: "desktop", width: 1440, height: 900 },
  ];
  const checks = [],
    shots = [];
  await fs.mkdir(root + "after", { recursive: true });
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    for (const [name, route] of Object.entries(refs.routes)) {
      await page.goto(base + route);
      await page.locator(selectors[name]).waitFor();
      await page.waitForFunction(
        () =>
          !document
            .querySelector(".connection")
            .textContent.includes("Kayıtlar alınıyor"),
      );
      const geometry = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth,
        smallTargets: [
          ...document.querySelectorAll(
            "main a,main button,main input,main select,main summary,.topbar a,.topbar button",
          ),
        ]
          .filter((e) => {
            const r = e.getBoundingClientRect();
            return (
              e.getClientRects().length &&
              e.checkVisibility() &&
              (r.width < 43.9 || r.height < 43.9)
            );
          })
          .map((e) => ({
            text:
              e.textContent.trim().slice(0, 70) || e.getAttribute("aria-label"),
            tag: e.tagName,
            width: e.getBoundingClientRect().width,
            height: e.getBoundingClientRect().height,
          })),
      }));
      let violations = [];
      if (["desktop", "mobile"].includes(viewport.name)) {
        const axe = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze();
        violations = axe.violations.map((v) => ({
          id: v.id,
          impact: v.impact,
          nodes: v.nodes.map((n) => ({
            target: n.target,
            summary: n.failureSummary,
          })),
        }));
        const path = "after/" + name + "-" + viewport.name + ".png";
        await page.screenshot({ path: root + path, fullPage: true });
        const png = await fs.readFile(root + path);
        shots.push({
          name,
          path,
          route,
          viewport: { width: viewport.width, height: viewport.height },
          image: { width: png.readUInt32BE(16), height: png.readUInt32BE(20) },
          full_page: true,
        });
      }
      checks.push({
        name,
        route,
        viewport,
        geometry,
        axe: ["desktop", "mobile"].includes(viewport.name)
          ? violations
          : "not run at this viewport",
      });
    }
  }
  // Show form ergonomics without sending a mutation to the frozen fixture.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(base + "/satislar");
  await page.getByRole("button", { name: "Yeni satış", exact: true }).click();
  await page.screenshot({
    path: root + "after/sale-form-mobile.png",
    fullPage: true,
  });
  const formAxe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  checks.push({
    name: "sale-form-mobile",
    axe: formAxe.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(base + "/");
  await page.locator(".overview-heading").waitFor();
  const motion = await page.evaluate(() => ({
    preference: matchMedia("(prefers-reduced-motion: reduce)").matches,
    animations: [...document.querySelectorAll("*")].filter(
      (e) => getComputedStyle(e).animationName !== "none",
    ).length,
  }));
  const failed = checks.filter(
    (c) =>
      c.geometry?.overflow ||
      c.geometry?.smallTargets.length ||
      (Array.isArray(c.axe) && c.axe.length),
  );
  await fs.writeFile(
    root + "after/manifest.json",
    JSON.stringify(shots, null, 2) + "\n",
  );
  await fs.writeFile(
    root + "visual-checks.json",
    JSON.stringify(
      {
        base_main: refs.base_main,
        database: refs.database,
        read_only: true,
        checks,
        reduced_motion: motion,
        page_errors: errors,
        failed: failed.length,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    JSON.stringify({
      screenshots: shots.length + 1,
      viewport_checks: checks.length - 1,
      axe_checks: 15,
      reduced_motion: motion,
      failures: failed.length,
      page_errors: errors,
    }),
  );
  if (failed.length || errors.length || !motion.preference || motion.animations)
    process.exitCode = 1;
} finally {
  await browser.close();
}
