const { test, expect } = require("@playwright/test");

const MASTER_CATEGORY_IDS = [
  "base_conversion",
  "binary_arithmetic",
  "unit_conversion",
  "number_of_values",
  "operators",
];

function formatBinary(value) {
  return value.toString(2).padStart(8, "0");
}

function formatHex(value) {
  return value.toString(16).toUpperCase().padStart(2, "0");
}

function formatAnswer(value) {
  return Number.isInteger(value) ? String(value) : String(value);
}

function solvePrompt(prompt) {
  const unitValues10 = {
    bit: 1,
    byte: 8,
    kilobyte: 8000,
    megabyte: 8000000,
    gigabyte: 8000000000,
  };
  const sizeUnits10 = { MB: 10 ** 6 * 8, GB: 10 ** 9 * 8 };
  const speedUnits = { "Mb/s": 10 ** 6, "Gb/s": 10 ** 9 };

  const trimmed = prompt.replace(/\r/g, "").trim();
  let match;

  match = trimmed.match(/^Convert ([0-9A-F]+) from (binary|denary|hexadecimal) to (binary|denary|hexadecimal)\.$/);
  if (match) {
    const [, rawValue, sourceBase, targetBase] = match;
    const baseMap = { binary: 2, denary: 10, hexadecimal: 16 };
    const value = parseInt(rawValue, baseMap[sourceBase]);
    if (targetBase === "binary") return formatBinary(value);
    if (targetBase === "denary") return String(value);
    return formatHex(value);
  }

  if (trimmed.startsWith("Add these 8-bit binary numbers:")) {
    const sum = [...trimmed.matchAll(/[01]{8}/g)].reduce((total, [, digits]) => total + parseInt(digits, 2), 0);
    return formatBinary(sum);
  }

  match = trimmed.match(/^Apply a (left|right) shift by (\d+) to the 8-bit binary number ([01]{8})\. Give the result in binary\.$/);
  if (match) {
    const [, direction, shiftText, digits] = match;
    const shift = Number(shiftText);
    const value = parseInt(digits, 2);
    const result = direction === "left" ? value << shift : value >> shift;
    return formatBinary(result);
  }

  match = trimmed.match(/^Convert (\d+) (bits|bytes|kilobytes|megabytes|gigabytes) to (bits|bytes|kilobytes|megabytes|gigabytes)\. You may use either base-10 or base-2 conventions\.$/);
  if (match) {
    const [, amountText, sourceUnit, targetUnit] = match;
    const amount = Number(amountText);
    return formatAnswer((amount * unitValues10[sourceUnit.slice(0, -1)]) / unitValues10[targetUnit.slice(0, -1)]);
  }

  match = trimmed.match(/^How long would it take to transfer a (\d+)(MB|GB) file at (\d+)(Mb\/s|Gb\/s)\? Give your answer in seconds\. \(You may use either base-2 or base-10 conventions\.\)$/);
  if (match) {
    const [, sizeText, sizeUnit, speedText, speedUnit] = match;
    const bits = Number(sizeText) * sizeUnits10[sizeUnit];
    return formatAnswer(bits / (Number(speedText) * speedUnits[speedUnit]));
  }

  match = trimmed.match(/^A file takes (\d+) seconds to transfer at (\d+)(Mb\/s|Gb\/s)\. What is the file size in (MB|GB)\? \(You may use either base-2 or base-10 conventions\.\)$/);
  if (match) {
    const [, timeText, speedText, speedUnit, targetUnit] = match;
    const bits = Number(timeText) * Number(speedText) * speedUnits[speedUnit];
    return formatAnswer(bits / sizeUnits10[targetUnit]);
  }

  match = trimmed.match(/^A (\d+)(MB|GB) file transfers in (\d+) seconds\. What is the average transmission speed in (Mb\/s|Gb\/s)\? \(You may use either base-2 or base-10 conventions for the file size\.\)$/);
  if (match) {
    const [, sizeText, sizeUnit, timeText, targetUnit] = match;
    const bits = Number(sizeText) * sizeUnits10[sizeUnit];
    return formatAnswer((bits / Number(timeText)) / speedUnits[targetUnit]);
  }

  match = trimmed.match(/^What is the highest value that can be represented with (\d+) (bits?|denary digits?)\?$/);
  if (match) {
    const [, countText, label] = match;
    const count = Number(countText);
    return label.startsWith("denary") ? String(10 ** count - 1) : String(2 ** count - 1);
  }

  match = trimmed.match(/^How many different values can be represented using (\d+) (bits?|denary digits?)\?$/);
  if (match) {
    const [, countText, label] = match;
    const count = Number(countText);
    return label.startsWith("denary") ? String(10 ** count) : String(2 ** count);
  }

  match = trimmed.match(/^Calculate (\d+) (DIV|MOD) (\d+)\.$/);
  if (match) {
    const [, leftText, op, rightText] = match;
    const left = Number(leftText);
    const right = Number(rightText);
    return String(op === "DIV" ? Math.floor(left / right) : left % right);
  }

  match = trimmed.match(/^Evaluate the boolean expression: (\d+) ([<>=≤≥]{1,2}) (\d+)\n\(Type True or False\)$/);
  if (match) {
    const [, leftText, op, rightText] = match;
    const left = Number(leftText);
    const right = Number(rightText);
    const result =
      op === "<" ? left < right :
      op === ">" ? left > right :
      op === "==" ? left === right :
      op === "≤" ? left <= right :
      left >= right;
    return result ? "True" : "False";
  }

  throw new Error(`Unsupported prompt: ${trimmed}`);
}

async function startSession(page) {
  await page.goto("/");

  await page.waitForFunction(() => typeof document.getElementById("btn-start").onclick === "function", null, {
    timeout: 120000,
  });

  await page.locator("#input-firstname").fill("Ada");
  await page.locator("#input-lastname").fill("Lovelace");
  await page.locator("#btn-start").click();
}

async function getTodayScoreTotal(page) {
  return page.evaluate((ids) =>
    ids.reduce((total, id) => total + Number(document.getElementById(`score-${id}-today`).textContent), 0),
  MASTER_CATEGORY_IDS);
}

async function getPromptText(row) {
  return row.evaluate((element) => element.children[1].innerText);
}

test("starts a session and renders questions", async ({ page }) => {
  await startSession(page);

  await expect(page.locator("#name-modal")).toHaveClass(/hidden/);
  await expect(page.locator("#label-student")).toHaveText("Ada Lovelace");

  const questions = page.locator("#questions-container .question-row");
  await expect(questions.first()).toBeVisible({ timeout: 60000 });
  expect(await questions.count()).toBeGreaterThan(0);
});

test("answers multiple questions without Pyodide proxy errors", async ({ page }) => {
  const consoleErrors = [];
  const pageErrors = [];

  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    pageErrors.push(String(error));
  });

  await startSession(page);

  const questions = page.locator("#questions-container .question-row");
  await expect(questions).toHaveCount(10);
  await expect(page.locator("#label-student")).toHaveText("Ada Lovelace");
  await expect.poll(() => getTodayScoreTotal(page)).toBe(0);

  const firstRow = questions.nth(0);
  const secondInput = questions.nth(1).locator("input[type='text']");
  await firstRow.locator("input[type='text']").fill(solvePrompt(await getPromptText(firstRow)));
  await expect.poll(() => getTodayScoreTotal(page)).toBe(1);
  await expect(secondInput).toBeFocused();

  const focusedInput = page.locator(".question-row input[type='text']").nth(1);
  await focusedInput.fill(solvePrompt(await getPromptText(questions.nth(1))));
  await expect.poll(() => getTodayScoreTotal(page)).toBe(2);
  await expect(questions.nth(2).locator("input[type='text']")).toBeFocused();

  const lastRow = questions.nth(9);
  const lastPrompt = await getPromptText(lastRow);
  await lastRow.locator("input[type='text']").fill(solvePrompt(lastPrompt));
  await expect.poll(() => getTodayScoreTotal(page)).toBe(3);
  await expect.poll(() => questions.count()).toBe(10);
  const replacementLastInput = questions.nth(9).locator("input[type='text']");
  await expect(replacementLastInput).toBeFocused({ timeout: 5000 });

  await replacementLastInput.fill(solvePrompt(await getPromptText(questions.nth(9))));
  await expect.poll(() => getTodayScoreTotal(page)).toBe(4);
  await expect.poll(() => questions.count()).toBe(10);

  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});
