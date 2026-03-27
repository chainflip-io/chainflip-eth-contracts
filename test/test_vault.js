const VaultContract = artifacts.require("Vault");
const KeyManagerContract = artifacts.require("KeyManager");

const NATIVE_ADDR = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE";

// Helper to assert a call reverts
async function assertReverts(promise, msg) {
  try {
    await promise;
    assert.fail(msg || "Expected revert but call succeeded");
  } catch (err) {
    // TronBox wraps reverts differently than Truffle — accept any error
    assert.ok(
      err.message && !err.message.includes("Expected revert but call succeeded"),
      msg || "Expected revert"
    );
  }
}

contract("Vault", (accounts) => {
  let vault;
  let keyManager;

  const govKey = accounts[0];
  const commKey = accounts[1];
  const alice = accounts[2];

  // Invalid sigData — will fail Schnorr verification
  const dummySigData = [0, 0, accounts[0]];

  before(async () => {
    // pubKeyX = 1 (valid: < HALF_Q), pubKeyYParity = 0
    keyManager = await KeyManagerContract.new([1, 0], govKey, commKey);
    vault = await VaultContract.new(keyManager.address);
  });

  it("transfer reverts with invalid signature", async () => {
    const transferParams = [NATIVE_ADDR, alice, 1000];
    await assertReverts(
      vault.transfer(dummySigData, transferParams, { from: alice }),
      "transfer should revert with invalid signature"
    );
  });

  it("transferBatch reverts with invalid signature", async () => {
    const transferParamsArray = [[NATIVE_ADDR, alice, 1000]];
    await assertReverts(
      vault.transferBatch(dummySigData, transferParamsArray, { from: alice }),
      "transferBatch should revert with invalid signature"
    );
  });

  it("allBatch reverts with invalid signature", async () => {
    const transferParamsArray = [[NATIVE_ADDR, alice, 1000]];
    await assertReverts(
      vault.allBatch(dummySigData, [], [], transferParamsArray, { from: alice }),
      "allBatch should revert with invalid signature"
    );
  });

  it("deployAndFetchBatch reverts with invalid signature", async () => {
    const swapID = "0x0000000000000000000000000000000000000000000000000000000000000001";
    const deployFetchParams = [[swapID, NATIVE_ADDR]];
    await assertReverts(
      vault.deployAndFetchBatch(dummySigData, deployFetchParams, { from: alice }),
      "deployAndFetchBatch should revert with invalid signature"
    );
  });

  it("fetchBatch reverts with invalid signature", async () => {
    const fetchParams = [[alice, NATIVE_ADDR]];
    await assertReverts(
      vault.fetchBatch(dummySigData, fetchParams, { from: alice }),
      "fetchBatch should revert with invalid signature"
    );
  });
});
