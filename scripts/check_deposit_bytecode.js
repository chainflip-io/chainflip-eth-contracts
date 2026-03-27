#!/usr/bin/env node

// This script checks that the Deposit contract's bytecode hasn't changed by
// computing CREATE2 addresses and comparing them against known expected values.
// This is the TronBox equivalent of the brownie test:
//   poetry run brownie test tests/unit/vault/test_deployAndFetchBatch.py::test_getCreate2Addr
//
// Run after `yarn tronbox compile`:
//   node scripts/check_deposit_bytecode.js

const fs = require("fs");
const path = require("path");
const TronWeb = require("tronweb");
const { keccak256, arrayify } = TronWeb.utils.ethersUtils;

function cleanHexStr(thing) {
  if (typeof thing === "string") {
    return thing.startsWith("0x") ? thing.slice(2) : thing;
  }
  return thing.toString(16);
}

function cleanHexStrPad(thing) {
  const cleaned = cleanHexStr(thing);
  return "0".repeat(64 - cleaned.length) + cleaned;
}

function getCreate2Addr(sender, saltHex, deployBytecode, argsHex) {
  const bytecodeWithArgs = deployBytecode + argsHex;
  const bytecodeHash = cleanHexStr(
    keccak256(arrayify("0x" + bytecodeWithArgs))
  );

  const payload = "41" + cleanHexStr(sender) + saltHex + bytecodeHash;

  const hash = keccak256(arrayify("0x" + payload));
  // Take the last 20 bytes
  return "0x" + cleanHexStr(hash).slice(-40);
}

const NATIVE_ADDR = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE";

// Load the compiled Deposit artifact
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
const depositBytecode = cleanHexStr(artifact.bytecode);

// Same values as the Rust TRON tests (test_tron_trx and test_tron_token)
const vaultAddress = "0xadeecfa46eb3579c0f733085ba69a296ae9ee743";
const usdtAddress = "0xeca9bc828a3005b9a3b909f2cc5c2a54794de05f";

// Test 1: CREATE2 with native token (TRX), salt = 0
const salt1 = cleanHexStrPad("0x0");
const depositAddr1 = getCreate2Addr(
  vaultAddress,
  salt1,
  depositBytecode,
  cleanHexStrPad(NATIVE_ADDR)
);
console.log("Deposit address (TRX):", depositAddr1);

const expectedAddr1 = "0xeb9b3220f5e1c7f719ce7b67d88b170f917c5999";
if (depositAddr1.toLowerCase() !== expectedAddr1.toLowerCase()) {
  console.error(
    `\nERROR: Deposit bytecode has changed! TRX CREATE2 address mismatch.\n` +
      `  Expected: ${expectedAddr1}\n` +
      `  Got:      ${depositAddr1}`
  );
  process.exit(1);
}

// Test 2: CREATE2 with USDT token, salt = 0
const salt2 = cleanHexStrPad("0x0");
const depositAddr2 = getCreate2Addr(
  vaultAddress,
  salt2,
  depositBytecode,
  cleanHexStrPad(usdtAddress)
);
console.log("Deposit address (USDT):", depositAddr2);

const expectedAddr2 = "0x73cf16c2bba473aec4ac5c17156a4c0e67f0fa10";
if (depositAddr2.toLowerCase() !== expectedAddr2.toLowerCase()) {
  console.error(
    `\nERROR: Deposit bytecode has changed! USDT CREATE2 address mismatch.\n` +
      `  Expected: ${expectedAddr2}\n` +
      `  Got:      ${depositAddr2}`
  );
  process.exit(1);
}

console.log(
  "\n✅ Deposit bytecode check passed! CREATE2 addresses match expected values."
);
