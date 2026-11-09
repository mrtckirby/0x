const { test, expect } = require("@playwright/test");
const { execFileSync } = require("child_process");
const path = require("path");
const { startScratchSession, openProfileMenu } = require("./ui-helpers");

async function answerFirstBaseConversion(page) {
  const question = page.locator(".question-row").first();
  const text = await question.innerText();
  const match = text.match(/Convert ([0-9A-F]+) from (binary|denary|hexadecimal) to (binary|denary|hexadecimal)\./);
  expect(match).not.toBeNull();
  const bases = { binary: 2, denary: 10, hexadecimal: 16 };
  const answer = parseInt(match[1], bases[match[2]]).toString(bases[match[3]]).toUpperCase();
  await question.locator("input[type=text]").fill(answer);
}

test("badge criteria use exact thresholds and all five categories", () => {
  const output = execFileSync("python3", [path.join(__dirname, "badge_checks.py")], { encoding: "utf8" });
  expect(output).toContain("ok");
});

test("available portraits load on their earned badges and remain compact", async ({ page }) => {
  await page.setViewportSize({ width: 1400, height: 900 });
  await page.addInitScript(() => {
    const usage = {};
    for (let day = 1; day <= 30; day++) usage[`2026-01-${String(day).padStart(2, "0")}`] = 300000;
    localStorage.setItem("cs_maths_state", JSON.stringify({
      firstname: "Ada", lastname: "Lovelace", last_active_date: new Date().toDateString(),
      advanced_mode: false, focus_category: null, focus_question_type: null,
      daily_scores: {},
      all_time_scores: { base_conversion: 25, binary_addition: 25, unit_conversion: 25, operators_div_mod: 25, bitwise_operators: 25 },
      daily_usage_ms: usage, usage_tracking_since: "2026-01-01",
    }));
  });
  await page.goto("/");
  await expect(page.locator("#label-student")).toHaveText("Ada", { timeout: 120000 });
  const portraits = {
    ada: "lovelace", hopper: "hopper", hamilton: "hamilton", knuth: "knuth", turing: "turing",
    shannon: "shannon", johnson: "johnson", boole: "boole", jones: "sparckjones", dijkstra: "dijkstra",
  };
  for (const [id, file] of Object.entries(portraits)) {
    const card = page.locator(`.badge-column [data-badge="${id}"]`);
    const image = card.locator("img");
    await expect(image).toHaveAttribute("src", `./badge-images/${file}.png`);
    await expect(image).toHaveAttribute("alt", "");
    await expect.poll(() => image.evaluate(el => el.complete && el.naturalWidth > 0)).toBe(true);
    const bounds = await image.boundingBox();
    expect(bounds.width).toBe(112);
    expect(bounds.height).toBe(112);
    expect((await card.boundingBox()).width).toBe(175);
  }
  await (await openProfileMenu(page)).locator("#btn-badges").click();
  for (const [id, file] of Object.entries(portraits)) {
    const image = page.locator(`#collection-${id} img`);
    await expect(image).toHaveAttribute("src", `./badge-images/${file}.png`);
    await expect.poll(() => image.evaluate(el => el.complete && el.naturalWidth > 0)).toBe(true);
  }
});

test("earned badges, collection, details and responsive layout", async ({ page }) => {
  const pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await page.setViewportSize({ width: 1400, height: 900 });
  await page.addInitScript(() => {
    localStorage.setItem("cs_maths_state", JSON.stringify({
      firstname: "Ada", lastname: "Lovelace", last_active_date: new Date().toDateString(),
      advanced_mode: false, focus_category: "base_conversion", focus_question_type: "base_conversion",
      daily_scores: {}, all_time_scores: { base_conversion: 9 },
      daily_usage_ms: { "2026-01-01": 600000 }, usage_tracking_since: "2026-01-01",
    }));
  });
  await page.goto("/");
  await expect(page.locator("#label-student")).toHaveText("Ada", { timeout: 120000 });
  const engagement = page.locator("#engagement-badges");
  const achievement = page.locator("#achievement-badges");
  await expect(engagement.getByRole("button", { name: /Ada Lovelace/ })).toBeVisible();
  await expect(engagement).not.toContainText("Grace Hopper");
  await expect(achievement.locator("button")).toHaveCount(0);
  await expect(page.locator("#badge-notice")).toBeHidden();

  await engagement.getByRole("button", { name: /Ada Lovelace/ }).click();
  await expect(page.locator("#badge-detail-modal")).toContainText("Analytical Engine");
  await expect(page.locator("#badge-detail-portrait")).toHaveAttribute("src", "./badge-images/lovelace.png");
  await expect(page.locator("#badge-detail-modal")).toContainText("10 minutes");
  await page.locator("#badge-detail-close").click();

  await answerFirstBaseConversion(page);
  const turing = achievement.getByRole("button", { name: /Alan Turing/ });
  await expect(turing).toBeVisible();
  await expect(turing).toHaveClass(/new-badge/);
  await expect(page.locator("#badge-announcement")).toContainText("Alan Turing");
  await expect(page.locator("#badge-notice")).toBeHidden({ timeout: 12000 });
  expect(pageErrors.filter(error => error.includes("dismiss_badge_notice"))).toEqual([]);

  await page.setViewportSize({ width: 700, height: 900 });
  await expect(engagement).toBeHidden();
  await expect(achievement).toBeHidden();
  await expect(page.locator("#questions-container")).toBeVisible();
  await (await openProfileMenu(page)).locator("#btn-badges").click();
  const collection = page.locator("#badges-modal");
  await expect(collection).toBeVisible();
  await expect(collection).toContainText("Grace Hopper · Keep Iterating (locked)");
  await expect(collection).toContainText("Practice days: 1 / 3");
  await expect(collection.locator("#collection-hopper img")).toHaveAttribute("src", "./badge-images/hopper.png");
  await expect.poll(() => collection.locator("#collection-hopper img").evaluate(el => el.complete && el.naturalWidth > 0)).toBe(true);
  await expect(collection).toHaveCSS("overflow", "hidden");
  await expect(collection).toHaveCSS("border-radius", "8px");
  const scroller = collection.locator(".dialog-scroll");
  expect(await scroller.evaluate(el => el.scrollHeight > el.clientHeight)).toBe(true);
  await scroller.evaluate(el => { el.scrollTop = el.scrollHeight; });
  expect(await scroller.evaluate(el => el.scrollTop)).toBeGreaterThan(0);
  await collection.getByRole("button", { name: /Alan Turing/ }).click();
  await expect(page.locator("#badge-detail-modal")).toContainText("10 correct answers");
  await page.locator("#badge-detail-close").click();
  await expect(collection).toBeVisible();
  await page.locator("#badges-close").click();
});

test("a badge notification can be dismissed before its timeout", async ({ page }) => {
  const pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await page.addInitScript(() => {
    localStorage.setItem("cs_maths_state", JSON.stringify({
      firstname: "Ada", lastname: "Lovelace", last_active_date: new Date().toDateString(),
      advanced_mode: false, focus_category: "base_conversion", focus_question_type: "base_conversion",
      daily_scores: {}, all_time_scores: { base_conversion: 9 },
      daily_usage_ms: {}, usage_tracking_since: null,
    }));
  });
  await page.goto("/");
  await expect(page.locator("#label-student")).toHaveText("Ada", { timeout: 120000 });
  await answerFirstBaseConversion(page);
  await expect(page.locator("#badge-notice")).toBeVisible();
  await page.locator("#badge-notice-close").click();
  await expect(page.locator("#badge-notice")).toBeHidden();
  await page.waitForTimeout(8500);
  expect(pageErrors.filter(error => error.includes("dismiss_badge_notice"))).toEqual([]);
});

test("restored and cleared progress updates badges without celebrating old awards", async ({ page }) => {
  await page.setViewportSize({ width: 1400, height: 900 });
  await startScratchSession(page, "Test", "Learner");
  await openProfileMenu(page);
  const backup = {
    firstname: "Ada", lastname: "Lovelace", last_active_date: new Date().toDateString(),
    advanced_mode: false, focus_category: null, focus_question_type: null,
    daily_scores: {}, all_time_scores: { base_conversion: 10 },
    daily_usage_ms: { "2026-01-01": 600000 }, usage_tracking_since: "2026-01-01",
  };
  await page.locator("#backup-file").setInputFiles({
    name: "progress.0xf", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(backup)),
  });
  await expect(page.locator('#achievement-badges [data-badge="turing"]')).toBeVisible();
  await expect(page.locator('#engagement-badges [data-badge="ada"]')).toBeVisible();
  await expect(page.locator(".new-badge")).toHaveCount(0);
  await expect(page.locator("#badge-notice")).toBeHidden();
  await page.reload();
  await expect(page.locator('#achievement-badges [data-badge="turing"]')).toBeVisible({ timeout: 120000 });
  await expect(page.locator(".new-badge")).toHaveCount(0);
  await (await openProfileMenu(page)).locator("#btn-start-over").click();
  await page.locator("#btn-confirm-reset").click();
  await expect(page.locator("#engagement-badges button, #achievement-badges button")).toHaveCount(0);
});
