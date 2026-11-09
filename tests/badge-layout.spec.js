const { test, expect } = require("@playwright/test");

test("questions stay centred and badges stay in their columns at every award state", async ({ page }) => {
  await page.route("https://pyscript.net/**", route => route.abort());
  await page.goto("/");

  for (const width of [700, 1099, 1100, 1400, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    for (const [engagement, achievement] of [[false, false], [true, false], [false, true], [true, true]]) {
      await page.evaluate(([left, right]) => {
        document.querySelector("#engagement-badges").textContent = left ? "Engagement badge" : "";
        document.querySelector("#achievement-badges").textContent = right ? "Achievement badge" : "";
      }, [engagement, achievement]);

      const layout = await page.locator(".practice-layout").boundingBox();
      const questions = await page.locator("#questions-container").boundingBox();
      expect(questions.width).toBeGreaterThan(600);
      expect(Math.abs((questions.x + questions.width / 2) - (layout.x + layout.width / 2))).toBeLessThan(1);
      expect(questions.width).toBeLessThanOrEqual(896);

      for (const [selector, present, side] of [
        ["#engagement-badges", engagement, "left"],
        ["#achievement-badges", achievement, "right"],
      ]) {
        const badge = page.locator(selector);
        if (width < 1100 || !present) {
          await expect(badge).toBeHidden();
        } else {
          await expect(badge).toBeVisible();
          const box = await badge.boundingBox();
          if (side === "left") expect(box.x + box.width).toBeLessThanOrEqual(questions.x);
          else expect(box.x).toBeGreaterThanOrEqual(questions.x + questions.width);
          expect(Math.abs(box.y - questions.y)).toBeLessThan(1);
        }
      }
    }
  }
});
