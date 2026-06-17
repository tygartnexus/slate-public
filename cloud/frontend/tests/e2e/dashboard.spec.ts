import { expect, test } from "@playwright/test";

test("dashboard lists uploaded verdict and shows evidence sections", async ({ page }) => {
  await page.goto("/dashboard");

  await expect(page.getByRole("heading", { name: "Verdicts" })).toBeVisible();
  await expect(page.getByText(/verdicts? uploaded/)).toBeVisible();
  await expect(page.getByText("e2e_gemma_public_001")).toBeVisible();
  await expect(page.getByText("FAIL").first()).toBeVisible();

  await page.getByText("e2e_gemma_public_001").click();

  await expect(page.getByText("e2e_gemma_public_001").first()).toBeVisible();
  await expect(page.getByText("confidence 82%")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence-based answer" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Facts" }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Assumptions" }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Unknowns" }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence" }).first()).toBeVisible();
  await expect(page.getByText("Failures (9)")).toBeVisible();

  await page.getByRole("button", { name: "Red Team Mode" }).click();
  await expect(page.getByRole("heading", { name: "Hostile red-team review" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Risks" }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Counterarguments" }).first()).toBeVisible();

  await page.getByRole("link", { name: "Access" }).click();
  await expect(page.getByRole("heading", { name: "Access" })).toBeVisible();
  await expect(page.getByText("All Slate features are free.")).toBeVisible();
});
