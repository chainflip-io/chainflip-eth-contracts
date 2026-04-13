const VaultContract = artifacts.require("Vault");
const KeyManagerContract = artifacts.require("KeyManager");

const NATIVE_ADDR = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE";

// Helper: convert hex address (41...) to base58 for tronWeb API calls
function toBase58(hexAddr) {
  return tronWeb.address.fromHex(hexAddr);
}

// tronWeb.trx.getBalance uses the solidity node (walletsolidity/getaccount)
// which is disabled on our java-tron node. Use getUnconfirmedBalance instead
// which queries the full node (wallet/getaccount).
async function getBalance(addr) {
  return tronWeb.trx.getUnconfirmedBalance(addr);
}

// Get transaction info, retrying until the tx is included in a block.
// TronBox returns the txId before it's mined, so we may need to wait.
async function getTxInfo(txId, retries = 10, delayMs = 1000) {
  for (let i = 0; i < retries; i++) {
    const info = await tronWeb.trx.getUnconfirmedTransactionInfo(txId);
    if (info && info.id) return info;
    await new Promise((r) => setTimeout(r, delayMs));
  }
  throw new Error(`Transaction ${txId} not found after ${retries} retries`);
}

// Assert that a transaction succeeded (did not revert)
function assertSuccess(info, msg) {
  assert.notEqual(info.receipt.result, "REVERT", `${msg}: tx reverted`);
}

// Check that a transaction receipt contains a specific event
function hasEvent(info, eventSignature) {
  // tronWeb.sha3 returns "0x..." but TRON tx info topics omit the prefix
  const topic = tronWeb.sha3(eventSignature).replace(/^0x/, "");
  return info.log?.some((l) => l.topics[0] === topic) || false;
}

contract("Vault", (accounts) => {
  let vault;
  let keyManager;

  // TronBox only has one account (from the single privateKey in tronbox.js).
  // Use a hardcoded EOA address as the transfer recipient (TRON hex format).
  const alice = "0x1111111111111111111111111111111111111111";
  const aliceBase58 = toBase58("41" + alice.slice(2));

  // Invalid sigData — will fail Schnorr verification
  const dummySigData = [0, 0, accounts[0]];

  before(async () => {
    vault = await VaultContract.deployed();
    keyManager = await KeyManagerContract.deployed();
  });

  it("setTransferConfig reverts with invalid signature", async () => {
    const tx = await vault.setTransferConfig(dummySigData, 0, {
      from: accounts[0],
    });
    const info = await getTxInfo(tx);
    assert.equal(
      info.receipt.result,
      "REVERT",
      "setTransferConfig should revert with invalid signature"
    );
  });

  // ---------------------------------------------------------------------------
  // Tests below require valid Schnorr signatures. To avoid rewriting the signer
  // logic in crypto.py but in javaScript, we'd ideally want to reuse the
  // python logic to precompute and then hardcode the signature data. However,
  // the contracta addresses are not deterministic and change on each deployment,
  // which makes the precomputed signatures invalid. For now we just comment out
  // the signature verification when running these tests in CI.
  // ---------------------------------------------------------------------------

  // Fund the vault before running these tests
  it("fund vault with native TRX", async () => {
    const vaultBase58 = toBase58(vault.address);
    await tronWeb.trx.sendTrx(vaultBase58, 1_000_000);
    const balance = await getBalance(vaultBase58);
    assert.ok(Number(balance) >= 1_000_000, "vault should have TRX balance");
  });

  it("allBatch transfers native to an EOA", async () => {
    const sigData = [
      "0x1", // sig (non-zero to pass input validation)
      "0x1", // nonce
      accounts[0], // kTimesGAddress
    ];

    const transferAmount = 100_000; // 0.1 TRX in SUN
    const transferParams = [[NATIVE_ADDR, alice, transferAmount]];

    const balanceBefore = await getBalance(aliceBase58);

    const tx = await vault.allBatch(sigData, [], [], transferParams, {
      from: accounts[0],
    });
    const info = await getTxInfo(tx);
    assertSuccess(info, "allBatch");

    const balanceAfter = await getBalance(aliceBase58);
    assert.ok(
      Number(balanceAfter) > Number(balanceBefore),
      "recipient balance should increase after native transfer"
    );
  });

  it("allBatch transfer to contract emits TransferNativeFailed", async () => {
    // Default transferConfig = ContractCheckWithFallbackEvent (0)
    // Transferring native to a contract should emit TransferNativeFailed

    const sigData = [
      "0x1", // sig (non-zero to pass input validation)
      "0x2", // nonce (must be different from previous test)
      accounts[0], // kTimesGAddress
    ];

    const transferAmount = 100_000;
    // Use the KeyManager contract as the recipient (it's a contract address)
    const transferParams = [[NATIVE_ADDR, keyManager.address, transferAmount]];

    const tx = await vault.allBatch(sigData, [], [], transferParams, {
      from: accounts[0],
    });
    const info = await getTxInfo(tx);
    assertSuccess(info, "allBatch");

    // Check that TransferNativeFailed was emitted
    assert.ok(
      hasEvent(info, "TransferNativeFailed(address,uint256)"),
      "TransferNativeFailed event should be emitted"
    );
  });

  it("setTransferConfig changes the configuration", async () => {
    const sigData = [
      "0x1", // sig (non-zero to pass input validation)
      "0x3", // nonce (must be different from previous tests)
      accounts[0], // kTimesGAddress
    ];

    // Change to SkipContractCheck (2)
    const newConfig = 2;

    const tx = await vault.setTransferConfig(sigData, newConfig, {
      from: accounts[0],
    });
    const info = await getTxInfo(tx);
    assertSuccess(info, "setTransferConfig");

    // Check that TransferConfigSet was emitted
    assert.ok(
      hasEvent(info, "TransferConfigSet(uint8,uint8)"),
      "TransferConfigSet event should be emitted"
    );

    // Verify the config was updated by reading the public storage variable
    const currentConfig = await vault.transferConfig();
    assert.equal(
      currentConfig.toString(),
      newConfig.toString(),
      "transferConfig should be updated to SkipContractCheck"
    );
  });

  it("allBatch transfer to contract emits TransferNativeSkipped", async () => {
    // First set transferConfig to ContractCheckWithoutFallbackEvent (1)
    const configSigData = [
      "0x1", // sig
      "0x4", // nonce
      accounts[0], // kTimesGAddress
    ];
    const configTx = await vault.setTransferConfig(configSigData, 1, {
      from: accounts[0],
    });
    const configInfo = await getTxInfo(configTx);
    assertSuccess(configInfo, "setTransferConfig to 1");

    const sigData = [
      "0x1", // sig (non-zero to pass input validation)
      "0x5", // nonce (must be different from previous tests)
      accounts[0], // kTimesGAddress
    ];

    const transferAmount = 100_000;
    // Use the KeyManager contract as the recipient (it's a contract address)
    const transferParams = [[NATIVE_ADDR, keyManager.address, transferAmount]];

    const tx = await vault.allBatch(sigData, [], [], transferParams, {
      from: accounts[0],
    });
    const info = await getTxInfo(tx);
    assertSuccess(info, "allBatch");

    // Check that TransferNativeSkipped was emitted
    assert.ok(
      hasEvent(info, "TransferNativeSkipped(address,uint256)"),
      "TransferNativeSkipped event should be emitted"
    );
  });
});
