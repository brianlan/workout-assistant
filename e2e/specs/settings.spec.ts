/**
 * E2E-08: Settings
 *
 * Configure AI API settings and verify persistence.
 */
import { test, expect } from "@playwright/test";

test.describe("Settings", () => {
  test("should display settings page with form fields", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByText("AI API Configuration")).toBeVisible();
    await expect(page.getByText("API Base URL")).toBeVisible();
    await expect(page.getByText("API Key")).toBeVisible();
    await expect(page.getByText("Model Name")).toBeVisible();
    await expect(page.getByText("Save Settings")).toBeVisible();
  });

  test("should save and reload settings", async ({ page }) => {
    await page.goto("/settings");

    // Fill in settings
    await page.getByPlaceholder("https://api.openai.com/v1").fill("https://api.test.com/v1");
    await page.getByPlaceholder("gpt-4").fill("test-model");
    await page.getByPlaceholder("Enter new API key").fill("test-api-key-12345");

    // Save
    await page.getByText("Save Settings").click();

    // Verify success message
    await expect(page.getByText("Settings saved successfully.")).toBeVisible();

    // Reload and verify persistence
    await page.reload();
    await expect(page.getByPlaceholder("https://api.openai.com/v1")).toHaveValue(
      "https://api.test.com/v1",
    );
    await expect(page.getByPlaceholder("gpt-4")).toHaveValue("test-model");
    // API key should be masked
    await expect(page.getByText(/Current:/)).toBeVisible();
  });
});
