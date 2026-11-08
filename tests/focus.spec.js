const { test, expect } = require("@playwright/test");
const { execFileSync } = require("child_process");
const path = require("path");

const categories = [
  "base_conversion", "binary_arithmetic", "unit_conversion",
  "operators", "bit_patterns",
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
  const row = page.locator(".question-row").first();
  const prompt = await row.locator(":scope > div").nth(1).innerText();
  const capacity = prompt.match(/(\d+) (bits?|denary digits?)/);
  let answer;
  if (capacity) {
    const base = capacity[2].startsWith("denary") ? 10 : 2;
    answer = String(base ** Number(capacity[1]) - (prompt.startsWith("What is the highest") ? 1 : 0));
  } else {
    const conversion = prompt.match(/^Convert ([0-9A-F]+) from (binary|denary|hexadecimal) to (binary|denary|hexadecimal)\.$/);
    const bases = { binary: 2, denary: 10, hexadecimal: 16 };
    const value = parseInt(conversion[1], bases[conversion[2]]);
    answer = value.toString(bases[conversion[3]]).toUpperCase();
    if (conversion[3] === "binary") answer = answer.padStart(8, "0");
    if (conversion[3] === "hexadecimal") answer = answer.padStart(2, "0");
  }
  await row.locator("input").fill(String(answer));
  await expect(page.locator("#score-base_conversion-today")).toHaveText("1");
  // Change focus before the answer animation removes the old row.
  const binaryFocus = page.locator('[data-focus="binary_arithmetic"]');
  await binaryFocus.click();
  await expectCategory(page, "binary_arithmetic");
  await expect(baseFocus).toHaveText("Focus on Base conversion");
  await page.waitForTimeout(1600);
  await expectCategory(page, "binary_arithmetic");
  await expect(page.locator("#score-base_conversion-today")).toHaveText("1");

  await page.reload();
  await expect(binaryFocus).toHaveText("×", { timeout: 120000 });
  await expectCategory(page, "binary_arithmetic");
  await expect(page.locator("#score-base_conversion-all")).toHaveText("1");
  await binaryFocus.click();
  await expect(binaryFocus).toHaveText("Focus on Binary arithmetic");
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
