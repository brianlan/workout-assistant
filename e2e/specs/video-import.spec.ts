/**
 * E2E-01 & E2E-02: Video Import (File Upload & URL)
 *
 * Import videos via file upload and URL import.
 */
import { test, expect } from "@playwright/test";
import path from "path";
import { execSync } from "child_process";
import fs from "fs";
import os from "os";

test.describe("Video Import", () => {
  test("should open import modal with file and URL tabs", async ({ page }) => {
    await page.goto("/");
    await page.getByText("+ Import Video").click();
    await expect(page.getByText("Import Video")).toBeVisible();
    await expect(page.getByText("File Upload")).toBeVisible();
    await expect(page.getByText("URL Import")).toBeVisible();
  });

  test("should show category selector in import modal", async ({ page }) => {
    // Create a category via API
    await page.request.post("/api/categories", {
      data: { name: "Test Workout" },
    });

    await page.goto("/");
    await page.getByText("+ Import Video").click();
    await expect(page.getByText("Select category...")).toBeVisible();
  });

  test("should switch between file and URL tabs", async ({ page }) => {
    await page.goto("/");
    await page.getByText("+ Import Video").click();

    // File tab is default
    await expect(page.getByText("Video File")).toBeVisible();

    // Switch to URL tab
    await page.getByText("URL Import").click();
    await expect(page.getByPlaceholder("https://youtube.com/watch?v=...")).toBeVisible();

    // Switch back to file tab
    await page.getByText("File Upload").click();
    await expect(page.getByText("Video File")).toBeVisible();
  });
});
