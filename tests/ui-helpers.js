const { expect } = require("@playwright/test");

async function startScratchSession(page, firstname = "Ada", lastname = "Lovelace") {
  await page.goto("/");
  await expect(page.locator("#welcome-modal")).toBeVisible({ timeout: 120000 });
  await page.locator("#btn-start-scratch").click();
  await expect(page.locator("#name-modal")).toBeVisible();
  await page.locator("#input-firstname").fill(firstname);
  await page.locator("#input-lastname").fill(lastname);
  await page.locator("#btn-start").click();
}

async function openProfileMenu(page) {
  const menu = page.locator("#profile-menu");
  if (!(await menu.isVisible())) {
    await page.locator("#profile-button").click();
  }
  await expect(menu).toBeVisible();
  return menu;
}

async function openSettings(page) {
  const menu = await openProfileMenu(page);
  await menu.locator("#btn-profile").click();
  const settings = page.locator("#settings-modal");
  await expect(settings).toBeVisible();
  return settings;
}

async function focusCategory(page, category) {
  const menu = page.locator("#focus-menu");
  if (!(await menu.isVisible())) await page.locator("#focus-button").click();
  await expect(menu).toBeVisible();
  const button = menu.locator(`[data-focus="${category}"]`);
  const group = button.locator("xpath=ancestor::details[1]");
  if (await group.count()) {
    if (!(await group.evaluate(element => element.open))) await group.locator("summary").click();
  }
  await button.click();
}

async function focusQuestionType(page, questionType) {
  const menu = page.locator("#focus-menu");
  if (!(await menu.isVisible())) await page.locator("#focus-button").click();
  await expect(menu).toBeVisible();
  const button = menu.locator(`[data-focus-type="${questionType}"]`);
  const group = button.locator("xpath=ancestor::details[1]");
  if (await group.count()) {
    if (!(await group.evaluate(element => element.open))) await group.locator("summary").click();
  }
  await button.click();
}

async function setAdvancedMode(page, checked) {
  const settings = await openSettings(page);
  const checkbox = settings.locator("#toggle-advanced-profile");
  if (checked) await checkbox.check();
  else await checkbox.uncheck();
  await settings.locator("#btn-save-name").click();
  await settings.locator("#settings-close").click();
}

module.exports = {
  startScratchSession,
  openProfileMenu,
  openSettings,
  focusCategory,
  focusQuestionType,
  setAdvancedMode,
};
