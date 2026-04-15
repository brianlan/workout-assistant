/**
 * E2E-09: Responsive Layout
 *
 * Verify UI works at various viewport widths.
 */
import { test, expect } from "@playwright/test";

const viewports = [
  { name: "mobile 320px", width: 320, height: 568 },
  { name: "mobile 375px", width: 375, height: 667 },
  { name: "tablet 768px", width: 768, height: 1024 },
  { name: "desktop 1920px", width: 1920, height: 1080 },
];

for (const viewport of viewports) {
  test.describe(`Responsive at ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("should render library page without horizontal scroll", async ({ page }) => {
      await page.goto("/");
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
    });

    test("should show app title", async ({ page }) => {
      await page.goto("/");
      await expect(page.getByText("Workout Assistant")).toBeVisible();
    });

    test("should show hamburger menu on mobile", async ({ page }) => {
      if (viewport.width < 768) {
        await page.goto("/");
        const menuButton = page.getByLabel("Toggle menu");
        await expect(menuButton).toBeVisible();
      }
    });
  });
}
