// yarn tronbox migrate --f 1 --to 1 --reset --network nile

const VaultContract = artifacts.require("Vault");
const KeyManagerContract = artifacts.require("KeyManager");
const MockUSDT = artifacts.require("MockUSDT");
const CFTester = artifacts.require("CFTester");
const DepositContract = artifacts.require("Deposit");
const { checkDepositBytecode } = require("../scripts/deposit_bytecode_check");

module.exports = async function (deployer, network) {
  console.log("Starting deployment on network:", network);

  // Verify Deposit bytecode matches the expected bytecode in the State Chain before proceeding with the deployment.
  checkDepositBytecode(DepositContract.bytecode);
  const deployerAccount = deployer.options.options.network_config.from;
  console.log("Using deployer account:", deployerAccount);

  // --- Deploy KeyManager and Vault (all networks) ---

  // Hardcoded dummy aggKey and zero commKey as this is how it will be initialized in live networks.
  await deployer.deploy(
    KeyManagerContract,
    [1, 2], // dummy aggKey
    deployerAccount,
    "0x0000000000000000000000000000000000000000" // commKey
  );

  const keyManagerInstance = await KeyManagerContract.deployed();
  const keyManagerAddress = keyManagerInstance.address;
  console.log("KeyManagerContract deployed at address:", keyManagerAddress);

  await deployer.deploy(VaultContract, keyManagerAddress);
  const vault = await VaultContract.deployed();
  console.log("VaultContract deployed at address:", vault.address);

  // --- Deploy optional test contracts ---
  // Deploying both CfTester and USDT to both localnet and nile for testing purposes.
  // We might end up not using the USDT contract on Nile.
  if (network === "localnet" || network === "nile") {
    console.log("\n=== Deploying optional test contracts (localnet) ===");

    // 20M USDT with 6 decimals
    const INIT_USD_SUPPLY = "20000000000000";
    await deployer.deploy(MockUSDT, "Tether USD", "USDT", INIT_USD_SUPPLY);
    const usdt = await MockUSDT.deployed();
    console.log("MockUSDT deployed at address:", usdt.address);

    await deployer.deploy(CFTester, vault.address);
    const cfTester = await CFTester.deployed();
    console.log("CFTester deployed at address:", cfTester.address);
  }

  console.log("\n=== Deployment complete ===\n");
};
