const { test } = require("@playwright/test");
const { execFileSync } = require("child_process");
const path = require("path");

test("Bit patterns generators, validators and mode gating", () => {
  const output = execFileSync("python3", [path.join(__dirname, "bit_patterns_checks.py")], { encoding: "utf8" });
  if (!output.includes("ok")) throw new Error(output);
});
