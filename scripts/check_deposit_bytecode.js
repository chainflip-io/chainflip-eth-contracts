#!/usr/bin/env node

// Standalone script to check that the Deposit contract's bytecode hasn't changed.
// Run after `yarn tronbox compile`:
//   node scripts/check_deposit_bytecode.js

const fs = require("fs");
const path = require("path");
const { checkDepositBytecode } = require("./deposit_bytecode_check");

const artifactPath = path.join(
  __dirname,
  "..",
  "build",
  "contracts",
  "Deposit.json"
);
if (!fs.existsSync(artifactPath)) {
  console.error(
    "Error: Deposit.json not found. Run `yarn tronbox compile` first."
  );
  process.exit(1);
}

const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));

try {
  checkDepositBytecode(artifact.bytecode);
} catch (e) {
  console.error("\nERROR:", e.message);
  process.exit(1);
}
