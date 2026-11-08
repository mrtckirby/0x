const { test, expect } = require("@playwright/test");
const { execFileSync } = require("child_process");
const path = require("path");
const { inflateSync } = require("zlib");

test("usage tracking accounts for idle time, day boundaries, persistence and reset", () => {
  const output = execFileSync("python3", [path.join(__dirname, "usage_checks.py")], { encoding: "utf8" });
  expect(output).toContain("ok");
});

test("the proposed export vector and category mapping match the app", () => {
  const output = execFileSync("python3", [path.join(__dirname, "export_format_checks.py")], { encoding: "utf8" });
  expect(output).toContain("ok");
});

test("export serializes scores and handles clipboard and form size failures", () => {
  const output = execFileSync("python3", [path.join(__dirname, "export_checks.py")], { encoding: "utf8" });
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
  await page.locator("#label-student").click();
  await page.locator("#btn-start-over").click();
  await page.locator("#btn-confirm-reset").click();
  await expect(page.locator("#time-today")).toHaveText("0s");
  expect(await page.evaluate(() => localStorage.getItem("cs_maths_state"))).toBeNull();
});

test("export copies a snapshot and offers manual copy on clipboard failure", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("cs_maths_state", JSON.stringify({
      firstname: "Ada", lastname: "Lovelace", last_active_date: new Date().toDateString(),
      daily_scores: { base_conversion: 1 }, all_time_scores: { base_conversion: 4, binary_shift: 2 },
      daily_usage_ms: { "2026-01-01": 30000 }, usage_tracking_since: "2026-01-01",
    }));
    window.exportTest = { fail: false, value: "" };
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: {
      writeText: async value => {
        if (window.exportTest.fail) throw new Error("Permission denied");
        window.exportTest.value = value;
      },
    } });
  });
  await page.goto("/");
  await expect(page.locator("#label-student")).toHaveText("Ada Lovelace", { timeout: 120000 });
  await page.locator("#label-student").click();
  await expect(page.locator("#btn-export")).toBeVisible();
  await page.locator("#btn-export").click();
  await expect(page.locator("#export-status")).toContainText("Scores copied");
  const encoded = await page.evaluate(() => window.exportTest.value);
  expect(encoded.startsWith("0X1.")).toBe(true);
  const snapshot = JSON.parse(inflateSync(Buffer.from(encoded.slice(4), "base64url")).toString());
  expect(snapshot.n).toEqual(["Ada", "Lovelace"]);
  expect(snapshot.s).toEqual({ base_conversion: 4, binary_shift: 2 });
  expect(snapshot.d).toEqual({ base_conversion: 1 });
  expect(snapshot.t["2026-01-01"]).toBe(1);
  await page.evaluate(() => { window.exportTest.fail = true; });
  await page.locator("#btn-export").click();
  await expect(page.locator("#export-status")).toContainText("Clipboard access failed");
  await expect(page.locator("#export-text")).toBeVisible();
  expect(await page.locator("#export-text").inputValue()).toMatch(/^0X1\./);
});
