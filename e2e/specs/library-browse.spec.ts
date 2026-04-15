/**
 * E2E-03: Library Browse & Play
 *
 * Browse library, filter by category, search, play video, edit metadata, delete.
 */
import { test, expect } from "@playwright/test";

test.describe("Library Browse", () => {
  test("should display the library page with navigation", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Video Library")).toBeVisible();
    await expect(page.getByText("Library")).toBeVisible();
    await expect(page.getByText("Plans")).toBeVisible();
    await expect(page.getByText("Settings")).toBeVisible();
  });

  test("should show empty state when no videos exist", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/No videos found/i)).toBeVisible();
  });

  test("should show category filter dropdown", async ({ page }) => {
    await page.goto("/");
    const categorySelect = page.locator("select").first();
    await expect(categorySelect).toBeVisible();
  });

  test("should show search input", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByPlaceholder("Search videos...")).toBeVisible();
  });

  test("should show import video button", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("+ Import Video")).toBeVisible();
  });
});
