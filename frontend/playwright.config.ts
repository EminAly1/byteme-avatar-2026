import { defineConfig } from "@playwright/test";
export default defineConfig({
  globalSetup: "./tests/browser/global-setup.ts",
  testDir: "./tests/browser",
  fullyParallel: false,
  workers: 1,
  timeout: 90000,
  retries: 0,
  reporter: "list",
  use: {
    actionTimeout: 10000,
    baseURL: "http://127.0.0.1:5173",
    viewport: { width: 1440, height: 900 },
    headless: true,
    screenshot: "only-on-failure",
    launchOptions: {
      executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
      args: ["--no-sandbox"],
    },
  },
});
