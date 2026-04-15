/**
 * E2E-07: Statistics
 *
 * View statistics dashboard with charts.
 */
import { test, expect } from "@playwright/test";

test.describe("Statistics", () => {
  test("should display stats page with summary cards", async ({ page }) => {
    await page.goto("/stats");
    await expect(page.locator("h1")).toContainText("Statistics");
  });

  test("should show completion rate card", async ({ page }) => {
    await page.goto("/stats");
    await expect(page.getByText("Completion Rate")).toBeVisible();
    await expect(page.getByText("Total Plans")).toBeVisible();
    await expect(page.getByText("Completed Items")).toBeVisible();
    await expect(page.getByText("Total Items")).toBeVisible();
  });

  test("should show empty state message when no data", async ({ page }) => {
    await page.goto("/stats");
    await expect(
      page.getByText("Complete some plan items to see statistics."),
    ).toBeVisible();
  });
});
