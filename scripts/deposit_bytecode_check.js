// Shared module for checking Deposit contract bytecode via CREATE2 address verification.
// Used by both the standalone check script and the migration.

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

// Same values as the Rust TRON tests (test_tron_trx and test_tron_token)
const VAULT_ADDRESS = "0xadeecfa46eb3579c0f733085ba69a296ae9ee743";
const USDT_ADDRESS = "0xeca9bc828a3005b9a3b909f2cc5c2a54794de05f";

const EXPECTED_TRX_ADDR = "0xeb9b3220f5e1c7f719ce7b67d88b170f917c5999";
const EXPECTED_USDT_ADDR = "0x73cf16c2bba473aec4ac5c17156a4c0e67f0fa10";

// Checks that the Deposit bytecode produces the expected CREATE2 addresses.
// Takes the bytecode as a hex string (with or without 0x prefix).
// Throws on mismatch.
function checkDepositBytecode(bytecodeHex) {
  const bytecode = cleanHexStr(bytecodeHex);
  const salt = cleanHexStrPad("0x0");

  const addr1 = getCreate2Addr(
    VAULT_ADDRESS,
    salt,
    bytecode,
    cleanHexStrPad(NATIVE_ADDR)
  );
  console.log("Deposit address (TRX):", addr1);

  if (addr1.toLowerCase() !== EXPECTED_TRX_ADDR.toLowerCase()) {
    throw new Error(
      `Deposit bytecode has changed! TRX CREATE2 address mismatch.\n` +
        `  Expected: ${EXPECTED_TRX_ADDR}\n` +
        `  Got:      ${addr1}`
    );
  }

  const addr2 = getCreate2Addr(
    VAULT_ADDRESS,
    salt,
    bytecode,
    cleanHexStrPad(USDT_ADDRESS)
  );
  console.log("Deposit address (USDT):", addr2);

  if (addr2.toLowerCase() !== EXPECTED_USDT_ADDR.toLowerCase()) {
    throw new Error(
      `Deposit bytecode has changed! USDT CREATE2 address mismatch.\n` +
        `  Expected: ${EXPECTED_USDT_ADDR}\n` +
        `  Got:      ${addr2}`
    );
  }

  console.log(
    "\nDeposit bytecode check passed! CREATE2 addresses match expected values."
  );
}

module.exports = { checkDepositBytecode };
