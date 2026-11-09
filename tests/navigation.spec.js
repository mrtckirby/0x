const { test, expect } = require("@playwright/test");
const { openProfileMenu } = require("./ui-helpers");

test("welcome, profile and focus menus support the rearranged keyboard-accessible flow", async ({ page }) => {
  await page.goto("/");
  const welcome = page.locator("#welcome-modal");
  await expect(welcome).toBeVisible({ timeout: 120000 });
  await expect(welcome).toHaveAttribute("role", "dialog");
  await expect(welcome).toHaveAttribute("aria-modal", "true");
  await expect(welcome.getByRole("button", { name: "Start from scratch" })).toBeVisible();
  await expect(welcome.getByRole("button", { name: "Load progress from a file" })).toBeVisible();

  await welcome.getByRole("button", { name: "Start from scratch" }).click();
  const nameForm = page.locator("#name-modal");
  await expect(nameForm).toBeVisible();
  await expect(nameForm.getByLabel("Firstname")).toBeVisible();
  await expect(nameForm.getByLabel("Lastname")).toBeVisible();
  const advancedAtStart = nameForm.getByLabel("Include advanced questions");
  await advancedAtStart.check();
  await page.locator("#input-firstname").fill("Ada");
  await page.locator("#input-lastname").fill("Lovelace");
  await page.locator("#btn-start").click();
  await expect(welcome).toBeHidden();
  await expect(nameForm).toBeHidden();
  await expect(page.locator("#label-student")).toHaveText("Ada");
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")).advanced_mode)).toBe(true);

  const profileButton = page.locator("#profile-button");
  await expect(profileButton).toHaveAttribute("aria-controls", "profile-menu");
  await expect(profileButton).toHaveAttribute("aria-expanded", "false");
  const profileMenu = await openProfileMenu(page);
  await expect(profileButton).toHaveAttribute("aria-expanded", "true");
  for (const id of ["btn-profile", "btn-scorecard", "btn-badges", "btn-export", "btn-save-backup", "btn-load-backup", "btn-start-over"]) {
    await expect(profileMenu.locator(`#${id}`)).toBeVisible();
    await expect(profileMenu.locator(`#${id}`)).toHaveText(/\.\.\.$/);
    await expect(profileMenu.locator(`#${id}`)).toHaveCSS("cursor", "pointer");
  }
  for (const id of ["backup-status", "export-result"]) {
    expect(await page.locator(`#${id}`).evaluate(element => element.closest("#profile-menu"))).toBeNull();
  }
  await page.keyboard.press("Escape");
  await expect(profileMenu).toBeHidden();
  await expect(profileButton).toBeFocused();
  await expect(profileButton).toHaveAttribute("aria-expanded", "false");

  const focusButton = page.locator("#focus-button");
  await expect(focusButton).toHaveText("Focus on...");
  await expect(focusButton).toHaveCSS("cursor", "pointer");
  const ribbonColor = await page.locator(".menu-ribbon").evaluate(el => getComputedStyle(el).backgroundColor);
  const dashboardColor = await page.locator(".menu-ribbon").evaluate(el => getComputedStyle(el.parentElement).backgroundColor);
  expect(ribbonColor).not.toBe(dashboardColor);
  const focusMenu = page.locator("#focus-menu");
  await expect(focusButton).toHaveAttribute("aria-controls", "focus-menu");
  await focusButton.click();
  await expect(focusMenu).toBeVisible();
  await expect(focusButton).toHaveAttribute("aria-expanded", "true");
  await expect(focusMenu.locator("details")).toHaveCount(5);
  const baseGroup = focusMenu.locator('[data-focus="base_conversion"]').locator("xpath=ancestor::details[1]");
  await expect(baseGroup.locator("summary")).toHaveText("Base conversion");
  await baseGroup.locator("summary").click();
  await expect(baseGroup.locator('[data-focus="base_conversion"]')).toHaveText("All Base conversion");
  await expect(baseGroup.locator('[data-focus="base_conversion"]')).toHaveAttribute("aria-pressed", "false");

  const binaryGroup = focusMenu.locator('[data-focus="binary_arithmetic"]').locator("xpath=ancestor::details[1]");
  await binaryGroup.locator("summary").click();
  await expect(binaryGroup.locator('[data-focus-type="binary_shift"]')).toHaveText("Binary shifts");
  await expect(binaryGroup.locator('[data-focus-type="binary_shift"]')).toHaveAttribute("aria-pressed", "false");
  await page.keyboard.press("Escape");
  await expect(focusMenu).toBeHidden();
  await expect(focusButton).toBeFocused();

  await (await openProfileMenu(page)).locator("#btn-profile").click();
  const settings = page.getByRole("dialog", { name: "Profile" });
  await expect(settings).toBeVisible();
  await expect(settings.locator("#time-today")).toBeVisible();
  await expect(settings.locator("#time-all")).toBeVisible();
  await expect(settings.locator("#settings-close")).toHaveCSS("cursor", "pointer");
  await expect(settings.locator("#btn-save-name")).toHaveCSS("cursor", "pointer");
  await expect(settings.locator("#toggle-advanced-profile")).toBeChecked();
  await settings.locator("#toggle-advanced-profile").uncheck();
  await settings.locator("#btn-save-name").click();
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem("cs_maths_state")).advanced_mode)).toBe(false);
  await settings.locator("#settings-close").click();
  await (await openProfileMenu(page)).locator("#btn-profile").click();
  await expect(page.locator("#toggle-advanced-profile")).not.toBeChecked();
});
