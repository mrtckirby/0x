const { test, expect } = require("@playwright/test");
const { execFileSync } = require("child_process");
const path = require("path");

test("badge criteria use exact thresholds and all five categories", () => {
  const output = execFileSync("python3", [path.join(__dirname, "badge_checks.py")], { encoding: "utf8" });
  expect(output).toContain("ok");
});

test("earned badges, collection, details and responsive layout", async ({ page }) => {
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
  await expect(page.locator("#label-student")).toHaveText("Ada Lovelace", { timeout: 120000 });
  const engagement = page.locator("#engagement-badges");
  const achievement = page.locator("#achievement-badges");
  await expect(engagement.getByRole("button", { name: /Ada Lovelace/ })).toBeVisible();
  await expect(engagement).not.toContainText("Grace Hopper");
  await expect(achievement.locator("button")).toHaveCount(0);
  await expect(page.locator("#badge-notice")).toBeHidden();

  await engagement.getByRole("button", { name: /Ada Lovelace/ }).click();
  await expect(page.locator("#badge-detail-modal")).toContainText("Analytical Engine");
  await expect(page.locator("#badge-detail-modal")).toContainText("10 minutes");
  await page.locator("#badge-detail-close").click();

  const question = page.locator(".question-row").first();
  const text = await question.innerText();
  const match = text.match(/Convert ([0-9A-F]+) from (binary|denary|hexadecimal) to (binary|denary|hexadecimal)\./);
  expect(match).not.toBeNull();
  const bases = { binary: 2, denary: 10, hexadecimal: 16 };
  const answer = parseInt(match[1], bases[match[2]]).toString(bases[match[3]]).toUpperCase();
  await question.locator("input[type=text]").fill(answer);
  const turing = achievement.getByRole("button", { name: /Alan Turing/ });
  await expect(turing).toBeVisible();
  await expect(turing).toHaveClass(/new-badge/);
  await expect(page.locator("#badge-announcement")).toContainText("Alan Turing");

  await page.setViewportSize({ width: 700, height: 900 });
  await expect(engagement).toBeHidden();
  await expect(achievement).toBeHidden();
  await expect(page.locator("#questions-container")).toBeVisible();
  await page.locator("#profile-button").click();
  await page.locator("#btn-badges").click();
  const collection = page.locator("#badges-modal");
  await expect(collection).toBeVisible();
  await expect(collection).toContainText("Grace Hopper · Keep Iterating (locked)");
  await expect(collection).toContainText("Practice days: 1 / 3");
  await collection.getByRole("button", { name: /Alan Turing/ }).click();
  await expect(page.locator("#badge-detail-modal")).toContainText("10 correct answers");
  await page.locator("#badge-detail-close").click();
  await expect(collection).toBeVisible();
  await page.locator("#badges-close").click();
});

test("restored and cleared progress updates badges without celebrating old awards", async ({ page }) => {
  await page.setViewportSize({ width: 1400, height: 900 });
  await page.goto("/");
  await expect(page.locator("#name-modal")).toBeVisible({ timeout: 120000 });
  await page.locator("#input-firstname").fill("Test");
  await page.locator("#input-lastname").fill("Learner");
  await page.locator("#btn-start").click();
  await page.locator("#profile-button").click();
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
  await page.locator("#profile-button").click();
  await page.locator("#btn-start-over").click();
  await page.locator("#btn-confirm-reset").click();
  await expect(page.locator("#engagement-badges button, #achievement-badges button")).toHaveCount(0);
});
