import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/apk-browser", workers: 1, fullyParallel: false,
  timeout: 60000, retries: 0, reporter: "list",
  // Never capture a live download capability in a failure artifact or trace.
  use: { baseURL: "http://127.0.0.1:5173", headless: true, screenshot: "off", trace: "off", video: "off",
    launchOptions: { executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium", args: ["--no-sandbox"] } },
});
