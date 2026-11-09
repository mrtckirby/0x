const { test, expect } = require("@playwright/test");
const { startScratchSession, openSettings, openProfileMenu } = require("./ui-helpers");

test("theme initializes and responds to system changes before PyScript loads", async ({ page }) => {
  await page.route("https://pyscript.net/**", route => route.abort());
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  const html = page.locator("html");
  await expect(html).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("#welcome-modal > div")).toHaveCSS("background-color", "rgb(31, 41, 55)");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(html).toHaveAttribute("data-theme", "light");
  expect(await page.evaluate(() => window.setThemePreference("dark"))).toBe(true);
  await page.reload();
  await expect(html).toHaveAttribute("data-theme", "dark");
  await page.emulateMedia({ colorScheme: "dark" });
  expect(await page.evaluate(() => window.setThemePreference("light"))).toBe(true);
  await expect(html).toHaveAttribute("data-theme", "light");
  expect(await page.evaluate(() => window.setThemePreference("system"))).toBe(true);
  await expect(html).toHaveAttribute("data-theme", "dark");
});

test("theme follows the system and profile overrides persist independently of progress", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await startScratchSession(page);
  const html = page.locator("html");
  await expect(html).toHaveAttribute("data-theme", "dark");
  await expect(page.locator(".question-row").first()).toHaveCSS("background-color", "rgb(31, 41, 55)");

  await page.emulateMedia({ colorScheme: "light" });
  await expect(html).toHaveAttribute("data-theme", "light");
  let settings = await openSettings(page);
  await expect(settings.locator("#settings-theme")).toHaveValue("system");
  await settings.locator("#settings-theme").selectOption("dark");
  await settings.locator("#btn-save-name").click();
  await expect(html).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator(".question-row")).toHaveCount(10, { timeout: 120000 });
  await expect(html).toHaveAttribute("data-theme", "dark");
  await page.emulateMedia({ colorScheme: "dark" });
  await page.emulateMedia({ colorScheme: "light" });
  await expect(html).toHaveAttribute("data-theme", "dark");

  settings = await openSettings(page);
  await expect(settings.locator("#settings-theme")).toHaveValue("dark");
  await settings.locator("#settings-theme").selectOption("light");
  await settings.locator("#settings-close").click();
  settings = await openSettings(page);
  await expect(settings.locator("#settings-theme")).toHaveValue("dark");
  await settings.locator("#settings-theme").selectOption("light");
  await settings.locator("#btn-save-name").click();
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(html).toHaveAttribute("data-theme", "light");

  settings = await openSettings(page);
  await settings.locator("#settings-theme").selectOption("system");
  await settings.locator("#btn-save-name").click();
  await expect(html).toHaveAttribute("data-theme", "dark");
  await (await openProfileMenu(page)).locator("#btn-start-over").click();
  await page.locator("#btn-confirm-reset").click();
  await expect(html).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(html).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("#welcome-modal")).toBeVisible({ timeout: 120000 });
});
