// yarn tronbox migrate --f 1 --to 1 --reset --network nile

const VaultContract = artifacts.require("Vault");
const KeyManagerContract = artifacts.require("KeyManager");
const MockUSDT = artifacts.require("MockUSDT");
const CFTester = artifacts.require("CFTester");
const DepositContract = artifacts.require("Deposit");
const { checkDepositBytecode } = require("../scripts/deposit_bytecode_check");

module.exports = async function (deployer, network) {
  console.log("Starting deployment on network:", network);

  // Verify Deposit bytecode hasn't changed before deploying
  checkDepositBytecode(DepositContract.bytecode);
  const deployerAccount = deployer.options.options.network_config.from;
  console.log("Using deployer account:", deployerAccount);

  // --- Deploy KeyManager and Vault (all networks) ---

  // TODO: Add reading environment variables for aggKey. I think we can hardcode the
  // govKey and commKey to zero for now, as that seems to be how we will set it up.
  await deployer.deploy(
    KeyManagerContract,
    [1, 2], // dummy aggKey
    deployerAccount,
    deployerAccount
  );

  const keyManagerInstance = await KeyManagerContract.deployed();
  const keyManagerAddress = keyManagerInstance.address;
  console.log("KeyManagerContract deployed at address:", keyManagerAddress);

  await deployer.deploy(VaultContract, keyManagerAddress);
  const vault = await VaultContract.deployed();
  console.log("VaultContract deployed at address:", vault.address);

  // --- Deploy optional test contracts (localnet only) ---
  if (network === "localnet") {
    console.log("\n=== Deploying optional test contracts (localnet) ===");

    // 20M USDT with 6 decimals
    const INIT_USD_SUPPLY = "20000000000000";
    await deployer.deploy(MockUSDT, "Tether USD", "USDT", INIT_USD_SUPPLY);
    const usdt = await MockUSDT.deployed();
    console.log("MockUSDT deployed at address:", usdt.address);

    await deployer.deploy(CFTester, vault.address);
    const cfTester = await CFTester.deployed();
    console.log("CFTester deployed at address:", cfTester.address);

    // TODO: Maybe deploy USDT on live networks too if we can't get a chunk of the real Testnet USDT
  }

  console.log("\n=== Deployment complete ===\n");
};
