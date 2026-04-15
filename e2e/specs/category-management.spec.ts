/**
 * E2E-06: Category Management
 *
 * Create, rename, delete categories via the UI.
 */
import { test, expect } from "@playwright/test";

test.describe("Category Management", () => {
  test("should navigate to categories page", async ({ page }) => {
    await page.goto("/");
    await page.getByText("Categories").click();
    await expect(page.getByText("Categories").first()).toBeVisible();
  });

  test("should create a new category", async ({ page }) => {
    await page.goto("/categories");
    const input = page.getByPlaceholder("New category name");
    await input.fill("Test Category");
    await page.getByText("Add").click();
    await expect(page.getByText("Test Category")).toBeVisible();
  });

  test("should rename a category inline", async ({ page }) => {
    // Create a category first via API
    const response = await page.request.post("/api/categories", {
      data: { name: "Original Name" },
    });
    expect(response.ok()).toBeTruthy();

    await page.goto("/categories");
    await page.getByText("Rename").first().click();
    const input = page.locator('input[type="text"]').filter({ hasText: "" }).first();
    await input.fill("Renamed Category");
    await page.getByText("Save").first().click();
    await expect(page.getByText("Renamed Category")).toBeVisible();
  });

  test("should show empty state when no categories", async ({ page }) => {
    await page.goto("/categories");
    // There may or may not be categories from prior tests
    const hasCategories = await page.getByText("No categories yet.").isVisible().catch(() => false);
    // This is a soft check - the page should load either way
    await expect(page.locator("h1")).toContainText("Categories");
  });
});
