const { test, expect } = require("@playwright/test");
const { execFileSync } = require("child_process");
const path = require("path");

const backup = {
  firstname: "Grace", lastname: "Hopper", advanced_mode: true,
  focus_category: "binary_arithmetic", focus_question_type: "binary_shift",
  last_active_date: new Date().toDateString(),
  daily_scores: { binary_shift: 2 }, all_time_scores: { binary_shift: 8, number_of_values: 3 },
  daily_usage_ms: { "2026-01-01": 123456 }, usage_tracking_since: "2026-01-01",
};

function file(value) {
  return { name: "backup.json", mimeType: "application/json", buffer: Buffer.from(value) };
}

test("backup schema and storage failures are handled", () => {
  const output = execFileSync("python3", [path.join(__dirname, "backup_checks.py")], { encoding: "utf8" });
  expect(output).toContain("ok");
});

test("edit name, download backup, reject invalid files and restore after confirmation", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#name-modal")).toBeVisible({ timeout: 120000 });
  await page.locator("#input-firstname").fill("Ada");
  await page.locator("#input-lastname").fill("Lovelace");
  await page.locator("#btn-start").click();
  await page.locator("#label-student").click();
  const modal = page.locator("#settings-modal");
  await expect(modal).toBeVisible();
  await modal.locator("#settings-firstname").fill("Augusta");
  await modal.locator("#btn-save-name").click();
  await expect(page.locator("#label-student")).toHaveText("Augusta Lovelace");
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")).firstname)).toBe("Augusta");
  const downloadPromise = page.waitForEvent("download");
  await modal.locator("#btn-save-backup").click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("0x-progress.json");
  const fs = require("fs");
  const downloaded = JSON.parse(fs.readFileSync(await download.path(), "utf8"));
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")));
  expect(downloaded).toEqual(stored);

  await modal.locator("#backup-file").setInputFiles(file('{"firstname":"bad"}'));
  await expect(modal.locator("#backup-status")).toContainText("Could not load backup");
  await expect(page.locator("#label-student")).toHaveText("Augusta Lovelace");
  page.once("dialog", dialog => dialog.dismiss());
  await modal.locator("#backup-file").setInputFiles(file(JSON.stringify(backup)));
  await expect(modal.locator("#backup-status")).toContainText("cancelled");
  await expect(page.locator("#label-student")).toHaveText("Augusta Lovelace");
  page.once("dialog", dialog => dialog.accept());
  await modal.locator("#backup-file").setInputFiles(file(JSON.stringify(backup)));
  await expect(modal.locator("#backup-status")).toContainText("Backup loaded.");
  await expect(page.locator("#label-student")).toHaveText("Grace Hopper");
  await expect(modal.locator("#settings-firstname")).toHaveValue("Grace");
  await expect(modal.locator("#settings-lastname")).toHaveValue("Hopper");
  await expect(page.locator("#score-binary_arithmetic-all")).toHaveText("8");
  await expect(page.locator("#toggle-advanced-top")).toBeChecked();
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")).focus_question_type)).toBe("binary_shift");
  await modal.locator("#settings-close").click();
  await page.reload();
  await expect(page.locator("#label-student")).toHaveText("Grace Hopper", { timeout: 120000 });
  expect((await page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")))).daily_usage_ms["2026-01-01"]).toBe(123456);
});

test("backup can be loaded on startup when localStorage is blocked", async ({ page }) => {
  await page.addInitScript(() => {
    for (const method of ["getItem", "setItem", "removeItem"]) {
      Storage.prototype[method] = function() { throw new DOMException("Blocked", "SecurityError"); };
    }
  });
  await page.goto("/");
  await expect(page.locator("#name-modal")).toBeVisible({ timeout: 120000 });
  await expect(page.locator("#initial-backup-status")).toContainText("storage is unavailable");
  page.once("dialog", dialog => dialog.accept());
  await page.locator("#initial-backup-file").setInputFiles(file(JSON.stringify(backup)));
  await expect(page.locator("#label-student")).toHaveText("Grace Hopper");
  await expect(page.locator("#backup-status")).toContainText("for this session");
  const downloadPromise = page.waitForEvent("download");
  await page.locator("#btn-save-backup").click();
  const downloaded = await downloadPromise;
  const fs = require("fs");
  const value = JSON.parse(fs.readFileSync(await downloaded.path(), "utf8"));
  expect(value.all_time_scores.binary_shift).toBe(8);
  expect(value.daily_usage_ms["2026-01-01"]).toBe(123456);
});

test("loading an older backup resets only its daily scores", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#name-modal")).toBeVisible({ timeout: 120000 });
  page.once("dialog", dialog => dialog.accept());
  await page.locator("#initial-backup-file").setInputFiles(file(JSON.stringify({ ...backup, last_active_date: "yesterday" })));
  await expect(page.locator("#backup-status")).toContainText("Backup loaded.");
  await expect(page.locator("#score-binary_arithmetic-today")).toHaveText("0");
  await expect(page.locator("#score-binary_arithmetic-all")).toHaveText("8");
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")));
  expect(saved.daily_scores).toEqual({});
  expect(saved.daily_usage_ms["2026-01-01"]).toBe(123456);
});
