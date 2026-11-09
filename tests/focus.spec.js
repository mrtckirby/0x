const { test, expect } = require("@playwright/test");
const { execFileSync } = require("child_process");
const path = require("path");
const { startScratchSession, openProfileMenu, focusCategory, focusQuestionType, setAdvancedMode } = require("./ui-helpers");

const categories = [
  "base_conversion", "binary_arithmetic", "unit_conversion",
  "operators", "bit_patterns",
];

test("focused selection respects category and advanced setting", () => {
  const output = execFileSync("python3", [path.join(__dirname, "focus_checks.py")], { encoding: "utf8" });
  expect(output).toContain("ok");
});

async function startSession(page) {
  await startScratchSession(page);
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
  const baseFocus = page.locator('#focus-menu [data-focus="base_conversion"]');
  await focusCategory(page, "base_conversion");
  await expectCategory(page, "base_conversion");
  await expect(page.locator("#focus-button")).toHaveText("Clear focus");
  await expect(page.locator("#focus-button")).not.toHaveAttribute("aria-expanded");
  await expect(page.locator("#focus-clear-icon")).toBeVisible();
  await expect(page.locator("#focus-search-icon")).toBeHidden();
  await expect(baseFocus).toHaveText("All Number bases");
  await expect(baseFocus).toHaveAttribute("aria-pressed", "true");
  for (const category of categories) {
    const score = page.locator(`.score-block[data-cat="${category}"]`);
    if (category === "base_conversion") await expect(score).not.toHaveClass(/focus-muted/);
    else await expect(score).toHaveClass(/focus-muted/);
  }
  await expect(page.locator('.score-block[data-cat="average"]')).not.toHaveClass(/focus-muted/);

  await (await openProfileMenu(page)).locator("#btn-scorecard").click();
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
  const binaryFocus = page.locator('#focus-menu [data-focus="binary_arithmetic"]');
  await page.getByRole("button", { name: "Clear focus" }).click();
  await focusCategory(page, "binary_arithmetic");
  await expectCategory(page, "binary_arithmetic");
  await expect(baseFocus).toHaveAttribute("aria-pressed", "false");
  await page.waitForTimeout(1600);
  await expectCategory(page, "binary_arithmetic");
  await expect(page.locator("#score-base_conversion-today")).toHaveText("1");

  await page.reload();
  await expect(binaryFocus).toHaveAttribute("aria-pressed", "true", { timeout: 120000 });
  await expectCategory(page, "binary_arithmetic");
  await expect(page.locator("#score-base_conversion-all")).toHaveText("1");
  await expect(page.getByRole("button", { name: "Clear focus" })).toBeVisible();
  await page.getByRole("button", { name: "Clear focus" }).click();
  await expect(binaryFocus).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator("#focus-button")).toHaveText("Focus on...");
  await expect(page.locator("#focus-button")).toHaveAttribute("aria-expanded", "false");
  await expect(page.locator("#focus-search-icon")).toBeVisible();
  await expect(page.locator("#focus-clear-icon")).toBeHidden();
  await expect(page.locator(".score-block.focus-muted")).toHaveCount(0);
  await expect(page.locator(".question-row")).toHaveCount(10);
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")).focus_category)).toBeNull();
});

test("start over clears the saved focus", async ({ page }) => {
  await startSession(page);
  await focusCategory(page, "operators");
  await expectCategory(page, "operators");
  await (await openProfileMenu(page)).locator("#btn-start-over").click();
  await page.locator("#btn-confirm-reset").click();
  await expect(page.locator("#welcome-modal")).toBeVisible();
  await expect(page.locator(".score-block.focus-muted")).toHaveCount(0);
  await expect(page.locator('#focus-menu [data-focus="operators"]')).toHaveText("All Operators");
  await expect.poll(() => page.evaluate(() => localStorage.getItem("cs_maths_state"))).toBeNull();
});

test("focus menu selects one question type and persists until cleared", async ({ page }) => {
  await startSession(page);
  const rows = page.locator("#questions-container .question-row");
  await focusQuestionType(page, "binary_shift");
  await expect(rows).toHaveCount(10);
  await expect.poll(() => rows.evaluateAll(elements => elements.map(el => el.dataset.questionType))).toEqual(Array(10).fill("binary_shift"));
  await expect(page.locator('.score-block[data-cat="base_conversion"]')).toHaveClass(/focus-muted/);
  await expect(page.locator('#focus-menu [data-focus="binary_arithmetic"]')).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator('#focus-menu [data-focus-type="binary_shift"]')).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(page.locator("#focus-button")).toBeVisible({ timeout: 120000 });
  await expect(page.locator('#focus-menu [data-focus-type="binary_shift"]')).toHaveAttribute("aria-pressed", "true", { timeout: 120000 });
  await expect(page.locator('#focus-menu [data-focus="binary_arithmetic"]')).toHaveAttribute("aria-pressed", "false");
  await expect(rows).toHaveCount(10);
  await expect.poll(() => rows.evaluateAll(elements => elements.map(el => el.dataset.questionType))).toEqual(Array(10).fill("binary_shift"));
  await (await openProfileMenu(page)).locator("#btn-scorecard").click();
  const dialog = page.locator("#scorecard");
  await expect(dialog.locator("[data-focus], [data-focus-type]")).toHaveCount(0);
  await page.getByRole("button", { name: "Close scorecard" }).click();
  await page.getByRole("button", { name: "Clear focus" }).click();
  await expect(page.locator(".score-block.focus-muted")).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => {
    const state = JSON.parse(localStorage.getItem("cs_maths_state"));
    return [state.focus_category, state.focus_question_type];
  })).toEqual([null, null]);
});

test("turning off advanced mode returns advanced type focus to its master category", async ({ page }) => {
  await startSession(page);
  await setAdvancedMode(page, true);
  await focusQuestionType(page, "binary_subtraction");
  const rows = page.locator("#questions-container .question-row");
  await expect.poll(() => rows.evaluateAll(elements => elements.map(el => el.dataset.questionType))).toEqual(Array(10).fill("binary_subtraction"));
  await setAdvancedMode(page, false);
  await expectCategory(page, "binary_arithmetic");
  await expect.poll(() => rows.evaluateAll(elements => elements.map(el => el.dataset.questionType))).not.toContain("binary_subtraction");
  await expect.poll(() => page.evaluate(() => {
    const state = JSON.parse(localStorage.getItem("cs_maths_state"));
    return [state.focus_category, state.focus_question_type];
  })).toEqual(["binary_arithmetic", null]);
});
