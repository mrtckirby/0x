const { test, expect } = require("@playwright/test");
const { startScratchSession } = require("./ui-helpers");

const MASTER_CATEGORY_IDS = [
  "base_conversion",
  "binary_arithmetic",
  "unit_conversion",
  "operators",
  "bit_patterns",
];
const UNIT_VALUES10 = {
  bit: 1,
  byte: 8,
  kilobyte: 8000,
  megabyte: 8000000,
  gigabyte: 8000000000,
};
const SIZE_UNITS10 = { MB: 10 ** 6 * 8, GB: 10 ** 9 * 8 };
const SPEED_UNITS = { "Mb/s": 10 ** 6, "Gb/s": 10 ** 9 };
const BASE_CONVERSION_PATTERN = /^Convert ([0-9A-F]+) from (binary|denary|hexadecimal) to (binary|denary|hexadecimal)\.$/;
const BIT_SHIFT_PATTERN = /^(Multiply|Divide) the 8-bit binary number ([01]{8}) by (\d+)(?:, discarding any remainder)?\. Give the result in binary\.$/;
const UNIT_CONVERSION_PATTERN = /^Convert (\d+) (bits|bytes|kilobytes|megabytes|gigabytes) to (bits|bytes|kilobytes|megabytes|gigabytes)\. You may use either base-10 or base-2 conventions\.$/;
const TRANSFER_TIME_PATTERN = /^How long would it take to transfer a (\d+(?:\.\d+)?)(MB|GB) file at (\d+)(Mb\/s|Gb\/s)\? Give your answer in seconds\. \(You may use either base-2 or base-10 conventions\.\)$/;
const TRANSFER_SIZE_PATTERN = /^A file takes (\d+(?:\.\d+)?) seconds to transfer at (\d+)(Mb\/s|Gb\/s)\. What is the file size in (MB|GB)\? \(You may use either base-2 or base-10 conventions\.\)$/;
const TRANSFER_SPEED_PATTERN = /^A (\d+(?:\.\d+)?)(MB|GB) file transfers in (\d+(?:\.\d+)?) seconds\. What is the average transmission speed in (Mb\/s|Gb\/s)\? \(You may use either base-2 or base-10 conventions for the file size\.\)$/;
const CAPACITY_HIGHEST_PATTERN = /^What is the highest value that can be represented with (\d+) (bits?|denary digits?)\?$/;
const CAPACITY_COUNT_PATTERN = /^How many different values can be represented using (\d+) (bits?|denary digits?)\?$/;
const DIV_MOD_PATTERN = /^Calculate (\d+) (DIV|MOD) (\d+)\.$/;
const BOOLEAN_PATTERN = /^Evaluate the boolean expression:\n(.+)\n\(Type True or False\)$/;
const BITWISE_PATTERN = /^Calculate (NOT )?([01]{4})(?: (AND|OR|XOR) ([01]{4}))?\. Give your answer as a 4-bit binary number\.$/;

function formatBinary(value) {
  return value.toString(2).padStart(8, "0");
}

function formatHex(value) {
  return value.toString(16).toUpperCase().padStart(2, "0");
}

function formatAnswer(value) {
  return String(value);
}

function solveBooleanExpression(expression) {
  const tokens = expression.match(/\d+|<=|>=|==|[<>=≤≥]|AND|OR|XOR|NOT|[()]/g) || [];
  if (expression.replace(/\s+/g, "") !== tokens.join("")) {
    throw new Error(`Unsupported boolean expression: ${expression}`);
  }
  let index = 0;
  const peek = () => tokens[index];
  const take = (expected) => {
    if (tokens[index] !== expected) throw new Error(`Expected ${expected} in boolean expression`);
    index += 1;
  };
  const parsePrimary = () => {
    if (peek() === "(") {
      take("(");
      const value = parseOr();
      take(")");
      return value;
    }
    const left = Number(tokens[index++]);
    const operator = tokens[index++];
    const right = Number(tokens[index++]);
    if (!Number.isFinite(left) || !Number.isFinite(right)) {
      throw new Error(`Invalid comparison in boolean expression: ${expression}`);
    }
    if (operator === "<") return left < right;
    if (operator === ">") return left > right;
    if (operator === "=" || operator === "==") return left === right;
    if (operator === "≤" || operator === "<=") return left <= right;
    if (operator === "≥" || operator === ">=") return left >= right;
    throw new Error(`Unsupported boolean operator: ${operator}`);
  };
  const parseUnary = () => {
    if (peek() === "NOT") {
      take("NOT");
      return !parseUnary();
    }
    return parsePrimary();
  };
  const parseAnd = () => {
    let value = parseUnary();
    while (peek() === "AND") {
      take("AND");
      const right = parseUnary();
      value = value && right;
    }
    return value;
  };
  const parseXor = () => {
    let value = parseAnd();
    while (peek() === "XOR") {
      take("XOR");
      value = value !== parseAnd();
    }
    return value;
  };
  function parseOr() {
    let value = parseXor();
    while (peek() === "OR") {
      take("OR");
      const right = parseXor();
      value = value || right;
    }
    return value;
  }
  const answer = parseOr();
  if (index !== tokens.length) throw new Error(`Unexpected token in boolean expression: ${tokens[index]}`);
  return answer ? "True" : "False";
}

function analyzePrompt(prompt) {
  const trimmed = prompt.replace(/\r/g, "").trim();
  let match;

  if (trimmed.startsWith("What is the minimum file size of the image shown")) {
    return { category: "bit_patterns", answer: null };
  }

  match = trimmed.match(BASE_CONVERSION_PATTERN);
  if (match) {
    const [, rawValue, sourceBase, targetBase] = match;
    const baseMap = { binary: 2, denary: 10, hexadecimal: 16 };
    const value = parseInt(rawValue, baseMap[sourceBase]);
    if (targetBase === "binary") return { category: "base_conversion", answer: formatBinary(value) };
    if (targetBase === "denary") return { category: "base_conversion", answer: String(value) };
    return { category: "base_conversion", answer: formatHex(value) };
  }

  if (trimmed.startsWith("Add these 8-bit binary numbers:")) {
    const sum = [...trimmed.matchAll(/[01]{8}/g)].reduce((total, matchText) => total + parseInt(matchText[0], 2), 0);
    return { category: "binary_arithmetic", answer: formatBinary(sum) };
  }

  match = trimmed.match(BIT_SHIFT_PATTERN);
  if (match) {
    const [, operation, digits, factorText] = match;
    const factor = Number(factorText);
    const value = parseInt(digits, 2);
    const result = operation === "Multiply" ? value * factor : Math.floor(value / factor);
    return { category: "binary_arithmetic", answer: formatBinary(result) };
  }

  match = trimmed.match(UNIT_CONVERSION_PATTERN);
  if (match) {
    const [, amountText, sourceUnit, targetUnit] = match;
    const amount = Number(amountText);
    return {
      category: "unit_conversion",
      answer: formatAnswer((amount * UNIT_VALUES10[sourceUnit.slice(0, -1)]) / UNIT_VALUES10[targetUnit.slice(0, -1)]),
    };
  }

  match = trimmed.match(TRANSFER_TIME_PATTERN);
  if (match) {
    const [, sizeText, sizeUnit, speedText, speedUnit] = match;
    const bits = Number(sizeText) * SIZE_UNITS10[sizeUnit];
    return {
      category: "unit_conversion",
      answer: formatAnswer(bits / (Number(speedText) * SPEED_UNITS[speedUnit])),
    };
  }

  match = trimmed.match(TRANSFER_SIZE_PATTERN);
  if (match) {
    const [, timeText, speedText, speedUnit, targetUnit] = match;
    const bits = Number(timeText) * Number(speedText) * SPEED_UNITS[speedUnit];
    return { category: "unit_conversion", answer: formatAnswer(bits / SIZE_UNITS10[targetUnit]) };
  }

  match = trimmed.match(TRANSFER_SPEED_PATTERN);
  if (match) {
    const [, sizeText, sizeUnit, timeText, targetUnit] = match;
    const bits = Number(sizeText) * SIZE_UNITS10[sizeUnit];
    return {
      category: "unit_conversion",
      answer: formatAnswer((bits / Number(timeText)) / SPEED_UNITS[targetUnit]),
    };
  }

  match = trimmed.match(CAPACITY_HIGHEST_PATTERN);
  if (match) {
    const [, countText, label] = match;
    const count = Number(countText);
    return {
      category: "base_conversion",
      answer: label.startsWith("denary") ? String(10 ** count - 1) : String(2 ** count - 1),
    };
  }

  match = trimmed.match(CAPACITY_COUNT_PATTERN);
  if (match) {
    const [, countText, label] = match;
    const count = Number(countText);
    return {
      category: "base_conversion",
      answer: label.startsWith("denary") ? String(10 ** count) : String(2 ** count),
    };
  }

  match = trimmed.match(DIV_MOD_PATTERN);
  if (match) {
    const [, leftText, op, rightText] = match;
    const left = Number(leftText);
    const right = Number(rightText);
    return { category: "operators", answer: String(op === "DIV" ? Math.floor(left / right) : left % right) };
  }

  match = trimmed.match(BITWISE_PATTERN);
  if (match) {
    const [, not, leftText, op, rightText] = match;
    const left = parseInt(leftText, 2);
    const right = rightText ? parseInt(rightText, 2) : 0;
    const value = not ? (~left & 0b1111) :
      op === "AND" ? left & right :
      op === "OR" ? left | right :
      left ^ right;
    return { category: "bit_patterns", answer: value.toString(2).padStart(4, "0") };
  }

  match = trimmed.match(BOOLEAN_PATTERN);
  if (match) {
    return { category: "operators", answer: solveBooleanExpression(match[1]) };
  }

  throw new Error(`Unsupported prompt: ${trimmed}`);
}

async function solvePrompt(prompt, row) {
  const analysis = analyzePrompt(prompt);
  if (analysis.answer !== null) return analysis.answer;
  const grid = row.locator('[role="img"]');
  const dimensions = (await grid.getAttribute("aria-label")).match(/(\d+) columns by (\d+) rows/);
  const colours = await grid.locator("[data-colour]").evaluateAll(
    cells => new Set(cells.map(cell => cell.getAttribute("data-colour"))).size
  );
  return String(Number(dimensions[1]) * Number(dimensions[2]) * Math.ceil(Math.log2(colours)));
}

function categoryForPrompt(prompt) {
  return analyzePrompt(prompt).category;
}

async function startSession(page) {
  await startScratchSession(page);
}

async function getTodayScoreTotal(page) {
  return page.evaluate((ids) =>
    ids.reduce((total, id) => total + Number(document.getElementById(`score-${id}-today`).textContent), 0),
  MASTER_CATEGORY_IDS);
}

async function getCategoryTodayScore(page, categoryId) {
  return page.evaluate((id) => Number(document.getElementById(`score-${id}-today`).textContent), categoryId);
}

async function getPromptText(row) {
  return row.evaluate((element) => element.children[1].innerText);
}

test("starts a session and renders questions", async ({ page }) => {
  await startSession(page);

  await expect(page.locator("#name-modal")).toHaveClass(/hidden/);
  await expect(page.locator("#label-student")).toHaveText("Ada");

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
  await expect(page.locator("#label-student")).toHaveText("Ada");
  await expect.poll(() => getTodayScoreTotal(page)).toBe(0);
  const expectedScores = Object.fromEntries(MASTER_CATEGORY_IDS.map((id) => [id, 0]));

  const firstRow = questions.nth(0);
  const firstPrompt = await getPromptText(firstRow);
  const secondInput = questions.nth(1).locator("input[type='text']");
  expectedScores[categoryForPrompt(firstPrompt)] += 1;
  await firstRow.locator("input[type='text']").fill(await solvePrompt(firstPrompt, firstRow));
  await expect.poll(() => getTodayScoreTotal(page)).toBe(1);
  await expect.poll(() => getCategoryTodayScore(page, categoryForPrompt(firstPrompt))).toBe(expectedScores[categoryForPrompt(firstPrompt)]);
  await expect(secondInput).toBeFocused();

  const focusedInput = page.locator(".question-row input[type='text']").nth(1);
  const secondPrompt = await getPromptText(questions.nth(1));
  expectedScores[categoryForPrompt(secondPrompt)] += 1;
  await focusedInput.fill(await solvePrompt(secondPrompt, questions.nth(1)));
  await expect.poll(() => getTodayScoreTotal(page)).toBe(2);
  await expect.poll(() => getCategoryTodayScore(page, categoryForPrompt(secondPrompt))).toBe(expectedScores[categoryForPrompt(secondPrompt)]);
  await expect(questions.nth(2).locator("input[type='text']")).toBeFocused();

  const lastRow = questions.nth(9);
  const lastPrompt = await getPromptText(lastRow);
  expectedScores[categoryForPrompt(lastPrompt)] += 1;
  await lastRow.locator("input[type='text']").fill(await solvePrompt(lastPrompt, lastRow));
  await expect.poll(() => getTodayScoreTotal(page)).toBe(3);
  await expect.poll(() => getCategoryTodayScore(page, categoryForPrompt(lastPrompt))).toBe(expectedScores[categoryForPrompt(lastPrompt)]);
  await expect.poll(() => questions.count()).toBe(10);
  const replacementLastInput = questions.nth(9).locator("input[type='text']");
  await expect(replacementLastInput).toBeFocused({ timeout: 5000 });

  const replacementLastPrompt = await getPromptText(questions.nth(9));
  expectedScores[categoryForPrompt(replacementLastPrompt)] += 1;
  await replacementLastInput.fill(await solvePrompt(replacementLastPrompt, questions.nth(9)));
  await expect.poll(() => getTodayScoreTotal(page)).toBe(4);
  await expect.poll(() => getCategoryTodayScore(page, categoryForPrompt(replacementLastPrompt))).toBe(expectedScores[categoryForPrompt(replacementLastPrompt)]);
  await expect.poll(() => questions.count()).toBe(10);

  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});

test("category colours are defined in CSS for every data-cat", async ({ page }) => {
  await page.goto("/");
  const keys = [...MASTER_CATEGORY_IDS, "average"];
  const values = await page.evaluate((cats) => cats.map((key) => {
    const el = document.createElement("div");
    el.setAttribute("data-cat", key);
    document.body.appendChild(el);
    const cs = getComputedStyle(el);
    const result = {
      cat: cs.getPropertyValue("--cat").trim(),
      text: cs.getPropertyValue("--cat-text").trim(),
    };
    el.remove();
    return result;
  }), keys);
  for (const v of values) {
    expect(v.cat).not.toBe("");
    expect(v.text).not.toBe("");
  }
  const catValues = values.slice(0, MASTER_CATEGORY_IDS.length).map((v) => v.cat);
  expect(new Set(catValues).size).toBe(MASTER_CATEGORY_IDS.length);
});

test("Bit patterns master category is visible and has no IP questions outside advanced mode", async ({ page }) => {
  await startSession(page);

  await expect(page.locator('[data-cat="bit_patterns"]').first()).toBeVisible();
  await expect(page.locator("#score-bit_patterns-today")).toHaveText("0");

  const questions = page.locator("#questions-container .question-row");
  await expect(questions).toHaveCount(10);
  const prompts = await questions.evaluateAll((rows) => rows.map((row) => row.children[1].innerText));
  for (const prompt of prompts) {
    expect(prompt).not.toMatch(/subnet|CIDR|Broadcast Address|Network Address|Host ID/i);
  }
});
