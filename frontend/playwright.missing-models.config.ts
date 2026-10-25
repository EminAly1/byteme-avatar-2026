import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/model-unavailable",
  globalSetup: "./tests/browser/global-setup.ts",
  workers: 1,
  retries: 0,
  timeout: 30000,
  reporter: "list",
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: false,
    timeout: 30000,
  },
  use: {
    baseURL: "http://127.0.0.1:5173",
    viewport: { width: 1440, height: 900 },
    headless: true,
    launchOptions: {
      executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
      args: ["--no-sandbox"],
    },
  },
});
