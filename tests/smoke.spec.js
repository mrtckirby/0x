const { test, expect } = require("@playwright/test");

test("starts a session and renders questions", async ({ page }) => {
  await page.goto("/");

  await page.waitForFunction(() => typeof document.getElementById("btn-start").onclick === "function", null, {
    timeout: 120000,
  });

  await page.locator("#input-firstname").fill("Ada");
  await page.locator("#input-lastname").fill("Lovelace");
  await page.locator("#btn-start").click();

  await expect(page.locator("#name-modal")).toHaveClass(/hidden/);
  await expect(page.locator("#label-student")).toHaveText("Ada Lovelace");

  const questions = page.locator("#questions-container .question-row");
  await expect(questions.first()).toBeVisible({ timeout: 60000 });
  expect(await questions.count()).toBeGreaterThan(0);
});
