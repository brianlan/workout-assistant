/**
 * E2E-04 & E2E-05: Plan Generation & Tracking
 *
 * Generate plans, view items, toggle completion, view history.
 */
import { test, expect } from "@playwright/test";

test.describe("Plans Page", () => {
  test("should display plans page with no active plan", async ({ page }) => {
    await page.goto("/plans");
    await expect(page.getByText(/No active plan/i)).toBeVisible();
    await expect(page.getByText("Generate Plan")).toBeVisible();
  });

  test("should show plan generation form", async ({ page }) => {
    await page.goto("/plans");
    await page.getByText("Generate Plan").click();
    await expect(page.getByText("Plan Parameters")).toBeVisible();
    await expect(page.getByText("Plan Type")).toBeVisible();
    await expect(page.getByText("Focus Areas")).toBeVisible();
  });
});

test.describe("Plan History", () => {
  test("should display plan history page", async ({ page }) => {
    await page.goto("/plans/history");
    await expect(page.locator("h1")).toContainText("Plan History");
  });

  test("should show empty state when no plans", async ({ page }) => {
    await page.goto("/plans/history");
    await expect(page.getByText("No plans yet.")).toBeVisible();
  });
});
