const { test, expect } = require("@playwright/test");
const { execFileSync } = require("child_process");
const path = require("path");

test("scorecard rendering matches the stored question types", () => {
  const output = execFileSync("python3", [path.join(__dirname, "scorecard_checks.py")], { encoding: "utf8" });
  expect(output).toContain("ok");
});

async function loadScores(page, lastActiveToday = true) {
  await page.addInitScript((today) => {
    localStorage.setItem("cs_maths_state", JSON.stringify({
      firstname: "Ada",
      lastname: "Lovelace",
      advanced_mode: false,
      last_active_date: today ? new Date().toDateString() : "previous day",
      daily_scores: { base_conversion: 2, number_of_values: 4, twos_comp_bin_to_den: 1, binary_addition: 3 },
      all_time_scores: { base_conversion: 7, number_of_values: 6, twos_comp_bin_to_den: 4, binary_addition: 8 },
    }));
  }, lastActiveToday);
  await page.goto("/");
  await expect(page.locator("#score-base_conversion-all")).toHaveText("17", { timeout: 120000 });
  await expect(page.locator("#score-base_conversion-today")).toHaveText(lastActiveToday ? "7" : "0");
  await expect(page.locator("#score-avg-all")).toHaveText("5.00");
}

test("category scorecard shows existing question types and closes from outside or X", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await loadScores(page);
  const trigger = page.locator('[data-scorecard="base_conversion"]');
  const dialog = page.locator("#scorecard");
  await trigger.click();
  await expect(dialog).toBeVisible();
  await expect(dialog.locator("#scorecard-title")).toHaveText("Base conversion");
  await expect(dialog.locator("[data-question-type]")).toHaveCount(2);
  await expect(dialog.locator('[data-question-type="base_conversion"] td')).toHaveText(["2", "7"]);
  await expect(dialog.locator('[data-question-type="number_of_values"] td')).toHaveText(["4", "6"]);
  await expect(dialog.locator('[data-question-type="twos_comp_bin_to_den"]')).toHaveCount(0);
  const triggerBox = await trigger.boundingBox();
  const dialogBox = await dialog.boundingBox();
  expect(dialogBox.y).toBeGreaterThan(triggerBox.y + triggerBox.height);
  expect(dialogBox.width).toBeLessThan(500);
  await page.mouse.click(10, 850);
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page.getByRole("button", { name: "Close scorecard" }).click();
  await expect(dialog).not.toBeVisible();
});

test("average scorecard contains all categories and their subtotals", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await loadScores(page);
  await page.locator('[data-scorecard="average"]').click();
  const dialog = page.locator("#scorecard");
  await expect(dialog.locator("#scorecard-title")).toHaveText("All scores");
  await expect(dialog.locator(".category-heading")).toHaveCount(5);
  await expect(dialog.locator("[data-question-type]")).toHaveCount(10);
  await expect(dialog.locator('.category-heading[data-cat="base_conversion"]')).toHaveText(/Base conversion\s+7\s+17/);
  await expect(dialog.locator('.category-heading[data-cat="binary_arithmetic"]')).toHaveText(/Binary arithmetic\s+3\s+8/);
  await expect(dialog.locator('[data-question-type="ip_host_id"]')).toHaveCount(0);
  await expect(dialog).toContainText("Category totals include advanced scores");
  expect((await dialog.boundingBox()).width).toBeGreaterThan(500);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
});

test("advanced mode reveals advanced types after standard types in both scorecards", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await loadScores(page);
  await page.locator("#toggle-advanced-top").check();
  await page.locator('[data-scorecard="bit_patterns"]').click();
  const dialog = page.locator("#scorecard");
  const expectedOrder = [
    "image_representation", "bitwise_operators", "ip_network_address", "ip_host_id",
    "ip_cidr_to_mask", "ip_mask_to_cidr", "ip_usable_hosts", "ip_min_subnet",
    "ip_broadcast_address", "ip_first_last_host",
  ];
  await expect.poll(() => dialog.locator("[data-question-type]").evaluateAll(
    rows => rows.map(row => row.getAttribute("data-question-type"))
  )).toEqual(expectedOrder);
  await page.getByRole("button", { name: "Close scorecard" }).click();
  await page.locator('[data-scorecard="average"]').click();
  await expect(dialog.locator("[data-question-type]")).toHaveCount(24);
  await expect(dialog.locator('[data-question-type="twos_comp_bin_to_den"] td')).toHaveText(["1", "4"]);
  const bitPatternRows = dialog.locator('.category-heading[data-cat="bit_patterns"] ~ [data-question-type]');
  await expect.poll(() => bitPatternRows.evaluateAll(
    rows => rows.map(row => row.getAttribute("data-question-type"))
  )).toEqual(expectedOrder);
  await expect(dialog).not.toContainText("Category totals include advanced scores");
  await page.keyboard.press("Escape");
  await page.locator("#toggle-advanced-top").uncheck();
  await page.locator('[data-scorecard="bit_patterns"]').click();
  await expect(dialog.locator("[data-question-type]")).toHaveCount(2);
});

test("mobile scorecard fills screen, scrolls and supports keyboard dismissal", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 600 });
  await loadScores(page, false);
  const trigger = page.locator('[data-scorecard="average"]');
  await trigger.focus();
  await page.keyboard.press("Enter");
  const dialog = page.locator("#scorecard");
  await expect(dialog).toBeVisible();
  const box = await dialog.boundingBox();
  expect(box).toMatchObject({ x: 0, y: 0, width: 390, height: 600 });
  await expect(dialog.locator('[data-question-type="base_conversion"] td')).toHaveText(["0", "7"]);
  expect(await dialog.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
  await expect(page.getByRole("button", { name: "Close scorecard" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
});
