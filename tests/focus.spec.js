const { test, expect } = require("@playwright/test");
const { execFileSync } = require("child_process");
const path = require("path");

const categories = [
  "base_conversion", "binary_arithmetic", "unit_conversion",
  "number_of_values", "operators", "bit_patterns",
];

test("focused selection respects category and advanced setting", () => {
  const output = execFileSync("python3", [path.join(__dirname, "focus_checks.py")], { encoding: "utf8" });
  expect(output).toContain("ok");
});

async function startSession(page) {
  await page.goto("/");
  await page.waitForFunction(() => typeof document.getElementById("btn-start").onclick === "function", null, {
    timeout: 120000,
  });
  await page.locator("#input-firstname").fill("Ada");
  await page.locator("#input-lastname").fill("Lovelace");
  await page.locator("#btn-start").click();
  await expect(page.locator(".question-row")).toHaveCount(10);
}

async function expectCategory(page, category) {
  const rows = page.locator(".question-row");
  await expect(rows).toHaveCount(10);
  await expect.poll(() => rows.locator(":scope > [data-cat]").evaluateAll(
    bars => bars.map(bar => bar.getAttribute("data-cat"))
  )).toEqual(Array(10).fill(category));
}

test("focus, switch, reload, and clear retain scores and refresh questions", async ({ page }) => {
  await startSession(page);
  const baseFocus = page.locator('[data-focus="base_conversion"]');
  await baseFocus.click();
  await expectCategory(page, "base_conversion");
  await expect(baseFocus).toHaveText("×");
  await expect(baseFocus).toHaveAttribute("aria-label", "Stop focusing on Base conversion");
  for (const category of categories) {
    const score = page.locator(`[data-scorecard="${category}"]`);
    if (category === "base_conversion") await expect(score).not.toHaveClass(/focus-muted/);
    else await expect(score).toHaveClass(/focus-muted/);
  }
  await expect(page.locator('[data-scorecard="average"]')).not.toHaveClass(/focus-muted/);

  await page.locator('[data-scorecard="operators"]').click();
  await expect(page.locator("#scorecard")).toBeVisible();
  await page.getByRole("button", { name: "Close scorecard" }).click();
  await page.locator('[data-focus="number_of_values"]').click();
  await expectCategory(page, "number_of_values");
  await expect(baseFocus).toHaveText("Focus on Base conversion");

  const row = page.locator(".question-row").first();
  const prompt = await row.locator(":scope > div").nth(1).innerText();
  const match = prompt.match(/(\d+) (bits?|denary digits?)/);
  const base = match[2].startsWith("denary") ? 10 : 2;
  const answer = base ** Number(match[1]) - (prompt.startsWith("What is the highest") ? 1 : 0);
  await row.locator("input").fill(String(answer));
  await expect(page.locator("#score-number_of_values-today")).toHaveText("1");
  // Change focus before the answer animation removes the old row.
  await baseFocus.click();
  await expectCategory(page, "base_conversion");
  await page.waitForTimeout(1600);
  await expectCategory(page, "base_conversion");
  await expect(page.locator("#score-number_of_values-today")).toHaveText("1");

  await page.reload();
  await expect(baseFocus).toHaveText("×", { timeout: 120000 });
  await expectCategory(page, "base_conversion");
  await expect(page.locator("#score-number_of_values-all")).toHaveText("1");
  await baseFocus.click();
  await expect(baseFocus).toHaveText("Focus on Base conversion");
  await expect(page.locator(".score-trigger.focus-muted")).toHaveCount(0);
  await expect(page.locator(".question-row")).toHaveCount(10);
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")).focus_category)).toBeNull();
});

test("start over clears the saved focus", async ({ page }) => {
  await startSession(page);
  await page.locator('[data-focus="operators"]').click();
  await expectCategory(page, "operators");
  await page.locator("#btn-start-over").click();
  await page.locator("#btn-confirm-reset").click();
  await expect(page.locator("#name-modal")).toBeVisible();
  await expect(page.locator(".score-trigger.focus-muted")).toHaveCount(0);
  await expect(page.locator('[data-focus="operators"]')).toHaveText("Focus on Operators");
  await expect.poll(() => page.evaluate(() => localStorage.getItem("cs_maths_state"))).toBeNull();
});
