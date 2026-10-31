import { test, expect } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { request as httpRequest } from "node:http";
import { createServer } from "node:net";
import path from "node:path";
import jsQR from "jsqr";
import { privateIpv4 } from "../../src/features/apk-download/status";

test("gerçek APK: yerel QR, üç genişlik, tek indirme, yenileme ve süre sonu", async ({ page }) => {
  const bind = process.env.AVATAR_APK_TEST_BIND || "";
  const expectedHash = process.env.AVATAR_APK_TEST_SHA256 || "";
  if (!privateIpv4(bind) || !/^[a-f0-9]{64}$/.test(expectedHash))
    throw new Error("Açık LAN onayı için AVATAR_APK_TEST_BIND ve doğrulanmış AVATAR_APK_TEST_SHA256 gerekli.");
  const root = path.resolve(import.meta.dirname, "../../..");
  const apk = await readFile(path.join(root, "android/app/build/outputs/apk/preview/app-preview.apk"));
  expect(createHash("sha256").update(apk).digest("hex") === expectedHash).toBe(true);
  const status = async () => {
    const r = await fetch("http://127.0.0.1:5173/api/apk-share", { headers: { "X-Avatar-Apk-Status": "1" } });
    if (r.status !== 200) throw new Error("Yerel web durum köprüsü hazır değil.");
    return r.json();
  };
  expect((await status()).state).toBe("inactive"); // Never interrupt an operator's active share.
  let child: ChildProcess | undefined;
  let output = "";
  async function start(ttl: number) {
    const listener = createServer();
    await new Promise<void>((resolve, reject) => { listener.once("error", reject); listener.listen(0, bind, resolve); });
    const port = (listener.address() as { port: number }).port;
    await new Promise<void>((resolve) => listener.close(() => resolve()));
    output = "";
    child = spawn("python3", ["tools/share_apk.py", "--sha256", expectedHash, "--bind", bind, "--allow-lan", "--port", String(port), "--ttl", String(ttl)],
      { cwd: root, stdio: ["ignore", "pipe", "pipe"] });
    child.stdout?.on("data", (b) => { output += b.toString(); });
    child.stderr?.on("data", (b) => { output += b.toString(); });
    await expect.poll(async () => {
      const s = await status(); return s.state === "active" && new URL(s.url).port === String(port);
    }, { timeout: 5000 }).toBe(true);
    expect(!output.includes("/download/")).toBe(true);
    return status();
  }
  async function stop() {
    if (child && child.exitCode === null && child.signalCode === null) {
      const exited = new Promise<void>((resolve) => child!.once("exit", () => resolve()));
      child.kill("SIGTERM"); await exited;
    }
    child = undefined;
  }
  function transfer(url: string, method = "GET"): Promise<{ code: number; body: Buffer; type?: string }> {
    return new Promise((resolve, reject) => {
      const r = httpRequest(url, { method, timeout: 2000 }, (res) => {
        const buffers: Buffer[] = []; res.on("data", (b) => buffers.push(b));
        res.on("end", () => resolve({ code: res.statusCode || 0, body: Buffer.concat(buffers), type: res.headers["content-type"] }));
        res.on("error", () => reject(new Error("Aktarım kesildi.")));
      });
      r.on("timeout", () => r.destroy()); r.on("error", () => reject(new Error("Paylaşım kapalı."))); r.end();
    });
  }
  const trigger = page.getByRole("button", { name: "Android Uygulamasını İndir", exact: true });
  const qr = page.getByRole("img", { name: "Geçerli APK indirme bağlantısının QR kodu" });
  const urlInput = page.getByRole("textbox", { name: "Geçici indirme bağlantısı" });
  const dialog = page.getByRole("dialog");
  async function noOverflow() {
    expect(await dialog.evaluate((el) => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
    const b = await dialog.boundingBox();
    expect(!!b && b.x >= 0 && b.x + b.width <= page.viewportSize()!.width + 1).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  try {
    // Catalog/business records are fixtures; bridge and APK are real services, never mocked.
    await page.route("**/api/v1/**", async (route) => {
      await route.fulfill({ json: route.request().url().includes("alerts/summary")
        ? { summary: { total: 0, critical: 0, warning: 0, info: 0 }, items: [] } : { items: [], next_cursor: null } });
    });
    await page.goto("/urunler");
    for (const width of [390, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await trigger.click();
      await expect(page.getByText("APK paylaşımı henüz başlatılmadı.", { exact: true })).toBeVisible();
      await noOverflow();
      await page.screenshot({ path: path.join(root, `docs/evidence/apk-qr-download/inactive-${width}.png`) });
      await page.keyboard.press("Escape"); await expect(dialog).toHaveCount(0); await expect(trigger).toBeFocused();
    }
    const first = await start(180);
    await trigger.click(); await expect(qr).toBeVisible();
    const close = page.getByRole("button", { name: "Ayrıntıyı kapat" });
    const refresh = page.getByRole("button", { name: "Paylaşımı kontrol et" });
    await expect(refresh).toBeEnabled();
    await close.focus(); await page.keyboard.press("Shift+Tab"); await expect(refresh).toBeFocused();
    await page.keyboard.press("Tab"); await expect(close).toBeFocused();
    await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
    await page.getByRole("button", { name: "İndirme bağlantısını kopyala" }).click();
    expect((await page.evaluate(() => navigator.clipboard.readText())) === first.url).toBe(true);
    expect((await urlInput.inputValue()) === first.url).toBe(true);
    // Independently rasterize the *rendered* QR and decode with jsQR, not the generator.
    const pixels = await qr.evaluate(async (svg) => {
      const blob = new Blob([new XMLSerializer().serializeToString(svg)], { type: "image/svg+xml" });
      const source = URL.createObjectURL(blob);
      try {
        const image = new Image(); image.src = source; await image.decode();
        const canvas = document.createElement("canvas"); canvas.width = canvas.height = 512;
        const ctx = canvas.getContext("2d")!; ctx.drawImage(image, 0, 0, 512, 512);
        return Array.from(ctx.getImageData(0, 0, 512, 512).data);
      } finally { URL.revokeObjectURL(source); }
    });
    const decoded = jsQR(new Uint8ClampedArray(pixels), 512, 512);
    expect(decoded?.data === first.url).toBe(true); // Never print the capability in assertions.
    for (const width of [390, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 }); await noOverflow();
      await page.screenshot({ path: path.join(root, `docs/evidence/apk-qr-download/active-masked-${width}.png`), mask: [qr, urlInput] });
    }
    await page.getByRole("button", { name: "Paylaşımı kontrol et" }).click();
    expect((await urlInput.inputValue()) === first.url).toBe(true);
    const origin = new URL(first.url).origin;
    for (const p of ["/", "/.env", "/status", "/v1/products", "/api/apk-share", "/download/wrong", "/../README.md"])
      expect((await transfer(origin + p)).code).toBe(404);
    expect((await transfer(first.url, "HEAD")).body.length).toBe(0);
    const download = await transfer(first.url);
    expect(download.code).toBe(200);
    expect(download.type).toBe("application/vnd.android.package-archive");
    expect(createHash("sha256").update(download.body).digest("hex") === expectedHash).toBe(true);
    let repeated = false;
    try { const r = await transfer(first.url); repeated = r.code === 200 && r.body.length > 0; } catch { /* closed after the only GET */ }
    expect(repeated).toBe(false);
    await expect(qr).toHaveCount(0); await stop();
    await expect.poll(async () => (await status()).state).toBe("inactive");
    const second = await start(5);
    expect(second.url !== first.url).toBe(true);
    await expect(qr).toBeVisible();
    expect((await urlInput.inputValue()) === second.url).toBe(true);
    await expect(qr).toHaveCount(0, { timeout: 8000 });
    await expect(page.getByText("Paylaşımın süresi doldu. Yeni indirme için paylaşımı yeniden başlatın.", { exact: true })).toBeVisible();
    await stop();
    let expiredServed = false;
    try { const r = await transfer(second.url); expiredServed = r.code === 200; } catch { /* closed after TTL */ }
    expect(expiredServed).toBe(false);
    await page.keyboard.press("Escape"); await expect(trigger).toBeFocused();
  } finally { await stop(); }
});
