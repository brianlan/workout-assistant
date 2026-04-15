import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./specs",
  timeout: 30000,
  retries: 0,
  use: {
    baseURL: "http://localhost:8000",
    headless: true,
  },
  webServer: {
    command: "../scripts/start.sh",
    port: 8000,
    reuseExistingServer: true,
  },
});
