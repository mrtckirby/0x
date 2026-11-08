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
  return { name: "backup.0xf", mimeType: "application/json", buffer: Buffer.from(value) };
}

test("backup schema and storage failures are handled", () => {
  const output = execFileSync("python3", [path.join(__dirname, "backup_checks.py")], { encoding: "utf8" });
  expect(output).toContain("ok");
});

for (const viewport of [{ width: 1280, height: 900 }, { width: 390, height: 600 }]) {
  test(`profile modal is centered and dimmed at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(page.locator("#name-modal")).toBeVisible({ timeout: 120000 });
    await page.locator("#input-firstname").fill("Ada");
    await page.locator("#input-lastname").fill("Lovelace");
    await page.locator("#btn-start").click();
    const profile = page.locator("#profile-button");
    await expect(profile.locator("svg")).toHaveCSS("cursor", "pointer");
    await expect(page.locator("#label-student")).toHaveCSS("cursor", "pointer");
    await profile.locator("svg").click();
    const modal = page.locator("#settings-modal");
    await expect(modal).toBeVisible();
    const bounds = await modal.boundingBox();
    expect(Math.abs(bounds.x + bounds.width / 2 - viewport.width / 2)).toBeLessThan(2);
    expect(Math.abs(bounds.y + bounds.height / 2 - viewport.height / 2)).toBeLessThan(2);
    expect(await modal.evaluate(el => getComputedStyle(el, "::backdrop").backgroundColor))
      .toBe("rgba(17, 24, 39, 0.6)");
    for (const label of ["Save progress to file...", "Load progress from file...",
      "Copy progress to clipboard...", "Clear progress..."]) {
      await expect(modal.getByRole("button", { name: label, exact: true })).toBeVisible();
      await expect(modal.getByRole("button", { name: label, exact: true }).locator("svg[aria-hidden='true']")).toHaveCount(1);
    }
    await modal.locator("#settings-close").click();
    await page.locator("#label-student").click();
    await expect(modal).toBeVisible();
    const chooser = page.waitForEvent("filechooser");
    await modal.getByRole("button", { name: "Load progress from file..." }).click();
    expect((await chooser).isMultiple()).toBe(false);
    await page.keyboard.press("Escape");
    await expect(modal).not.toBeVisible();
    await expect(profile).toBeFocused();
  });
}

test("edit name, download backup, reject invalid files and restore without confirmation", async ({ page }) => {
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
  await expect(modal).not.toBeVisible();
  expect(download.suggestedFilename()).toBe("Augusta-Lovelace.0xf");
  const fs = require("fs");
  const downloaded = JSON.parse(fs.readFileSync(await download.path(), "utf8"));
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")));
  expect(downloaded).toEqual(stored);

  await page.locator("#label-student").click();
  await modal.locator("#backup-file").setInputFiles(file('{"firstname":"bad"}'));
  await expect(modal.locator("#backup-status")).toContainText("Could not load backup");
  await expect(page.locator("#label-student")).toHaveText("Augusta Lovelace");
  const dialogs = [];
  page.on("dialog", dialog => { dialogs.push(dialog.message()); return dialog.dismiss(); });
  await modal.locator("#backup-file").setInputFiles(file(JSON.stringify(backup)));
  await expect(page.locator("#label-student")).toHaveText("Grace Hopper");
  await expect(modal).not.toBeVisible();
  expect(dialogs).toEqual([]);
  await page.locator("#label-student").click();
  await expect(modal.locator("#backup-status")).toBeEmpty();
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
  const chooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Load progress from a backup file" }).click();
  const chooser = await chooserPromise;
  await chooser.setFiles(file(JSON.stringify(backup)));
  await expect(page.locator("#label-student")).toHaveText("Grace Hopper");
  await expect(page.locator("#name-modal")).not.toBeVisible();
  await expect(page.locator("#settings-modal")).not.toBeVisible();
  await expect(page.locator("#storage-warning")).toContainText("storage is unavailable");
  await page.locator("#label-student").click();
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
  await page.locator("#initial-backup-file").setInputFiles(file(JSON.stringify({ ...backup, last_active_date: "yesterday" })));
  await expect(page.locator("#name-modal")).not.toBeVisible();
  await expect(page.locator("#settings-modal")).not.toBeVisible();
  await expect(page.locator("#score-binary_arithmetic-today")).toHaveText("0");
  await expect(page.locator("#score-binary_arithmetic-all")).toHaveText("8");
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")));
  expect(saved.daily_scores).toEqual({});
  expect(saved.daily_usage_ms["2026-01-01"]).toBe(123456);
});

test("backup filename replaces unsafe filename characters", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#name-modal")).toBeVisible({ timeout: 120000 });
  await page.locator("#input-firstname").fill("Eva/A");
  await page.locator("#input-lastname").fill("B:con");
  await page.locator("#btn-start").click();
  await page.locator("#label-student").click();
  const downloadPromise = page.waitForEvent("download");
  await page.locator("#btn-save-backup").click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("Eva_A-B_con.0xf");
  await expect(page.locator("#settings-modal")).not.toBeVisible();
});
