// yarn tronbox migrate --f 8 --to 8 --network localnet

const MockUSDT = artifacts.require("MockUSDT");
const CFTester = artifacts.require("CFTester");

module.exports = async function (deployer) {
  const vaultAddress = process.env.VAULT_ADDRESS;

  // --- Deploy MockUSDT ---
  console.log("\n=== Deploying MockUSDT ===");

  // 20M USDT with 6 decimals
  const INIT_USD_SUPPLY = "20000000000000";

  await deployer.deploy(MockUSDT, "Tether USD", "USDT", INIT_USD_SUPPLY);

  const usdt = await MockUSDT.deployed();
  console.log("MockUSDT deployed at address:", usdt.address);

  // --- Deploy CFTester ---
  console.log("\n=== Deploying CFTester ===");

  if (!vaultAddress) {
    throw new Error("VAULT_ADDRESS environment variable is required");
  }
  console.log("Using Vault address:", vaultAddress);

  await deployer.deploy(CFTester, vaultAddress);

  const cfTester = await CFTester.deployed();
  console.log("CFTester deployed at address:", cfTester.address);

  console.log("\n=== Deployment complete ===\n");
};
