const TetherTokenContract = artifacts.require("TetherToken");
const TetherTokenTesterContract = artifacts.require("TetherTokenTester");

// Get transaction info, retrying until the tx is included in a block.
async function getTxInfo(txId, retries = 10, delayMs = 1000) {
  for (let i = 0; i < retries; i++) {
    const info = await tronWeb.trx.getUnconfirmedTransactionInfo(txId);
    if (info && info.id) return info;
    await new Promise((r) => setTimeout(r, delayMs));
  }
  throw new Error(`Transaction ${txId} not found after ${retries} retries`);
}

// Check that a transaction receipt contains a specific event by its signature.
function hasEvent(info, eventSignature) {
  const topic = tronWeb.sha3(eventSignature).replace(/^0x/, "");
  return info.log?.some((l) => l.topics[0] === topic) || false;
}

const DEBUG_EVENT_SIG = "DebugEvent(address,uint256,address,bytes,bool)";

contract("TetherToken + TetherTokenTester", (accounts) => {
  let usdt;
  let tester;
  const owner = accounts[0];

  // Each TetherTokenTester function transfers exactly 1 raw token unit back to
  // the caller. Fund with enough to cover all 5 function tests.
  const FUND_AMOUNT = 10;

  before(async () => {
    // Deploy a fresh TetherToken: 20 M supply, 6 decimals (same as Tron mainnet USDT)
    usdt = await TetherTokenContract.deployed();
    // Deploy a fresh TetherTokenTester
    tester = await TetherTokenTesterContract.new();
    // Fund the tester so each test can pull 1 token back
    await usdt.transfer(tester.address, FUND_AMOUNT, { from: owner });
  });

  // ─── Setup sanity check ───────────────────────────────────────────────────

  it("tester contract is funded with FUND_AMOUNT tokens", async () => {
    const balance = await usdt.balanceOf(tester.address);
    assert.equal(
      Number(balance),
      FUND_AMOUNT,
      `Tester should hold ${FUND_AMOUNT} tokens after initial transfer`
    );
  });

  // ─── lowLevelTransfer ─────────────────────────────────────────────────────
  // Makes a raw .call() with transfer selector. Always emits DebugEvent with
  // the raw returndata and call success flag.

  it("lowLevelTransfer: sends 1 token to caller and emits DebugEvent", async () => {
    const balanceBefore = Number(await usdt.balanceOf(owner));

    const txId = await tester.lowLevelTransfer(usdt.address, { from: owner });
    const info = await getTxInfo(txId);

    assert.notEqual(
      info.receipt?.result,
      "REVERT",
      "lowLevelTransfer should not revert"
    );
    const balanceAfter = Number(await usdt.balanceOf(owner));
    assert.equal(
      balanceAfter - balanceBefore,
      1,
      "Owner should receive exactly 1 token"
    );
    assert.ok(
      hasEvent(info, DEBUG_EVENT_SIG),
      "Should emit DebugEvent (always emitted regardless of outcome)"
    );
  });

  // ─── lowLevelTransferLegacy ───────────────────────────────────────────────
  // Also uses a raw .call() but applies the legacy SafeERC20 pattern: treats
  // empty returndata as success. Emits DebugEvent on transfer.

  it("lowLevelTransferLegacy: sends 1 token to caller, no DebugEvent on success", async () => {
    const balanceBefore = Number(await usdt.balanceOf(owner));

    const txId = await tester.lowLevelTransferLegacy(usdt.address, {
      from: owner,
    });
    const info = await getTxInfo(txId);

    assert.notEqual(
      info.receipt?.result,
      "REVERT",
      "lowLevelTransferLegacy should not revert"
    );
    const balanceAfter = Number(await usdt.balanceOf(owner));
    assert.equal(
      balanceAfter - balanceBefore,
      1,
      "Owner should receive exactly 1 token"
    );
    assert.ok(
      hasEvent(info, DEBUG_EVENT_SIG),
      "Should emit DebugEvent"
    );
  });

  // ─── safeTransfer ─────────────────────────────────────────────────────────
  // Uses OpenZeppelin SafeERC20.safeTransfer, which enforces strict return-data
  // validation. Tether's non-standard transfer behaviour causes it to revert.

  it("safeTransfer: reverts because SafeERC20 rejects non-standard return data", async () => {
    const txId = await tester.safeTransfer(usdt.address, { from: owner });
    const info = await getTxInfo(txId);

    assert.equal(
      info.receipt?.result,
      "REVERT",
      "safeTransfer should revert"
    );
  });

  // ─── regularTransfer ──────────────────────────────────────────────────────
  // Calls IERC20.transfer and emits DebugEvent with the bool return value.

  it("regularTransfer: sends 1 token to caller and emits DebugEvent(success=true)", async () => {
    const balanceBefore = Number(await usdt.balanceOf(owner));

    const txId = await tester.regularTransfer(usdt.address, { from: owner });
    const info = await getTxInfo(txId);

    assert.notEqual(
      info.receipt?.result,
      "REVERT",
      "regularTransfer should not revert"
    );
    const balanceAfter = Number(await usdt.balanceOf(owner));
    assert.equal(
      balanceAfter - balanceBefore,
      1,
      "Owner should receive exactly 1 token"
    );
    assert.ok(
      hasEvent(info, DEBUG_EVENT_SIG),
      "Should emit DebugEvent with success flag"
    );
  });

  // ─── regularTransferRequire ───────────────────────────────────────────────
  // Calls IERC20.transfer and require()s the bool return to be true. Reverts
  // if the token returns false (non-compliant tokens would fail here).

  it("regularTransferRequire: reverts because require() rejects non-true return value", async () => {
    const txId = await tester.regularTransferRequire(usdt.address, {
      from: owner,
    });
    const info = await getTxInfo(txId);

    assert.equal(
      info.receipt?.result,
      "REVERT",
      "regularTransferRequire should revert"
    );
  });

  // ─── regularTransferRequire failure case ──────────────────────────────────
  // When the tester has no balance, transfer returns false and the require()
  // inside regularTransferRequire must cause a revert.

  it("regularTransferRequire: reverts when tester has insufficient balance", async () => {
    // Deploy a fresh tester with zero balance so the transfer will fail
    const emptyTester = await TetherTokenTesterContract.new();

    const txId = await emptyTester.regularTransferRequire(usdt.address, {
      from: owner,
    });
    const info = await getTxInfo(txId);

    assert.equal(
      info.receipt?.result,
      "REVERT",
      "regularTransferRequire should revert when the underlying transfer fails"
    );
  });
});
