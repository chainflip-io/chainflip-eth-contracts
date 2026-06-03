const KeyManagerContract = artifacts.require("KeyManager");

const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
const TRON_ZERO_ADDRESS = "410000000000000000000000000000000000000000";

contract("KeyManager", (accounts) => {
  let keyManager;

  const govKey = accounts[0];
  const commKey = accounts[1];

  beforeEach(async () => {
    keyManager = await KeyManagerContract.deployed();
  });

  it("setGovKeyWithGovKey accepts zero address", async () => {
    await keyManager.setGovKeyWithGovKey(ZERO_ADDRESS, { from: govKey });
    const newGov = await keyManager.getGovernanceKey();
    assert.equal(
      newGov,
      TRON_ZERO_ADDRESS,
      "governance key should be zero address"
    );
  });

  it("setCommKeyWithCommKey accepts zero address", async () => {
    await keyManager.setCommKeyWithCommKey(ZERO_ADDRESS, { from: commKey });
    const newComm = await keyManager.getCommunityKey();
    assert.equal(
      newComm,
      TRON_ZERO_ADDRESS,
      "community key should be zero address"
    );
  });

  it("setGovKeyWithGovKey reverts if not governor", async () => {
    try {
      await keyManager.setGovKeyWithGovKey(accounts[2], { from: accounts[2] });
      assert.fail("Expected revert but call succeeded");
    } catch (err) {
      assert.ok(
        err.message &&
          !err.message.includes("Expected revert but call succeeded"),
        "Expected revert"
      );
    }
  });

  it("setCommKeyWithCommKey reverts if not community key", async () => {
    try {
      await keyManager.setCommKeyWithCommKey(accounts[2], {
        from: accounts[2],
      });
      assert.fail("Expected revert but call succeeded");
    } catch (err) {
      assert.ok(
        err.message &&
          !err.message.includes("Expected revert but call succeeded"),
        "Expected revert"
      );
    }
  });
});
