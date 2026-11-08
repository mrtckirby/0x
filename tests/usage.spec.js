const { test, expect } = require("@playwright/test");
const { execFileSync } = require("child_process");
const path = require("path");

test("usage tracking accounts for idle time, day boundaries, persistence and reset", () => {
  const output = execFileSync("python3", [path.join(__dirname, "usage_checks.py")], { encoding: "utf8" });
  expect(output).toContain("ok");
});

test("the proposed export vector and category mapping match the app", () => {
  const output = execFileSync("python3", [path.join(__dirname, "export_format_checks.py")], { encoding: "utf8" });
  expect(output).toContain("ok");
});

test("usage is displayed and saved in a browser session", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#name-modal")).toBeVisible({ timeout: 120000 });
  await page.locator("#input-firstname").fill("Ada");
  await page.locator("#input-lastname").fill("Lovelace");
  await page.locator("#btn-start").click();
  await expect(page.locator("#time-today")).not.toHaveText("0s", { timeout: 15000 });
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")));
  expect(saved.usage_tracking_since).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  expect(saved.daily_usage_ms[saved.usage_tracking_since]).toBeGreaterThan(0);
  await page.reload();
  await expect(page.locator("#label-student")).toHaveText("Ada Lovelace", { timeout: 120000 });
  await expect(page.locator("#time-today")).not.toHaveText("0s");
  await page.locator("#btn-start-over").click();
  await page.locator("#btn-confirm-reset").click();
  await expect(page.locator("#time-today")).toHaveText("0s");
  expect(await page.evaluate(() => localStorage.getItem("cs_maths_state"))).toBeNull();
});
