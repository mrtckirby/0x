const { test, expect } = require("@playwright/test");
const { execFileSync } = require("child_process");
const path = require("path");
const { setAdvancedMode, openProfileMenu } = require("./ui-helpers");

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

for (const viewport of [{ width: 1280, height: 600 }, { width: 390, height: 600 }]) {
  test(`scorecard is centered, scrollable and dismissible at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await loadScores(page, false);
    const blocks = page.locator(".score-block");
    await expect(blocks).toHaveCount(6);
    await expect(page.locator("[data-scorecard]")).toHaveCount(0);
    await blocks.first().click();
    await expect(page.locator("#scorecard")).toBeHidden();
    await (await openProfileMenu(page)).locator("#btn-scorecard").click();
    const dialog = page.locator("#scorecard");
    await expect(dialog).toBeVisible();
    await expect(dialog.locator("#scorecard-title")).toHaveText("All scores");
    await expect(dialog.locator(".category-heading")).toHaveCount(5);
    await expect(dialog.locator("[data-question-type]")).toHaveCount(10);
    await expect(dialog.locator('.category-heading[data-cat="base_conversion"] th, .category-heading[data-cat="base_conversion"] td'))
      .toHaveText(["Number bases", "0", "17"]);
    await expect(dialog.locator('[data-question-type="base_conversion"] td')).toHaveText(["0", "7"]);
    await expect(dialog.locator('[data-question-type="unit_conversion"] th')).toHaveText("Data sizes");
    await expect(dialog).toContainText("Category totals include advanced scores");
    const box = await dialog.boundingBox();
    expect(Math.abs(box.x + box.width / 2 - viewport.width / 2)).toBeLessThan(2);
    expect(Math.abs(box.y + box.height / 2 - viewport.height / 2)).toBeLessThan(2);
    await expect(dialog).toHaveCSS("overflow", "hidden");
    await expect(dialog).toHaveCSS("border-radius", "8px");
    const scroller = dialog.locator(".dialog-scroll");
    expect(await scroller.evaluate(el => el.scrollHeight > el.clientHeight)).toBe(true);
    await scroller.evaluate(el => { el.scrollTop = el.scrollHeight; });
    expect(await scroller.evaluate(el => el.scrollTop)).toBeGreaterThan(0);
    await expect(dialog.locator("#scorecard-close")).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(page.locator("#profile-button")).toBeFocused();
    await (await openProfileMenu(page)).locator("#btn-scorecard").click();
    await page.mouse.click(1, 1);
    await expect(dialog).toBeHidden();
    await expect(page.locator("#profile-button")).toBeFocused();
  });
}

test("advanced mode reveals advanced types after standard types", async ({ page }) => {
  await loadScores(page);
  await setAdvancedMode(page, true);
  await (await openProfileMenu(page)).locator("#btn-scorecard").click();
  const dialog = page.locator("#scorecard");
  await expect(dialog.locator("[data-question-type]")).toHaveCount(24);
  await expect(dialog.locator('[data-question-type="twos_comp_bin_to_den"] td')).toHaveText(["1", "4"]);
  const bitPatternRows = dialog.locator('.category-heading[data-cat="bit_patterns"] ~ [data-question-type]');
  await expect.poll(() => bitPatternRows.evaluateAll(rows => rows.map(row => row.getAttribute("data-question-type")))).toEqual([
    "image_representation", "bitwise_operators", "ip_network_address", "ip_host_id",
    "ip_cidr_to_mask", "ip_mask_to_cidr", "ip_usable_hosts", "ip_min_subnet",
    "ip_broadcast_address", "ip_first_last_host",
  ]);
  await expect(dialog).not.toContainText("Category totals include advanced scores");
  await page.locator("#scorecard-close").click();
  await setAdvancedMode(page, false);
  await (await openProfileMenu(page)).locator("#btn-scorecard").click();
  await expect(dialog.locator("[data-question-type]")).toHaveCount(10);
});
