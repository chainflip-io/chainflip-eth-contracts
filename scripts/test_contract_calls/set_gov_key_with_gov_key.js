// To run, move this file to the migrations/ folder as "2_set_gov_key_with_gov_key.js" and run:
// yarn tronbox migrate --f 2 --to 2 --network nile

const KeyManagerContract = artifacts.require("KeyManager");

module.exports = async function (deployer, network, accounts) {
  console.log("\n=== Calling setGovKeyWithGovKey on existing KeyManager ===");
  const deployerAccount = deployer.options.options.network_config.from;
  console.log("Using deployer account (current govKey):", deployerAccount);

  // Load the existing KeyManager contract at the deployed address
  const keyManagerAddress = "TZEQtGkPWPFLSXQyEiQCJZQnzRpxCVb5zT";

  console.log("Loading KeyManager at address:", keyManagerAddress);
  const keyManager = await KeyManagerContract.at(keyManagerAddress);

  console.log("KeyManager loaded successfully!");
  console.log("KeyManager address (hex):", keyManager.address);

  // New governance key address
  const newGovKey = deployerAccount;

  console.log("\nCalling setGovKeyWithGovKey with parameters:");
  console.log("- newGovKey:", newGovKey);

  try {
    const tx = await keyManager.setGovKeyWithGovKey(newGovKey, {
      from: deployerAccount,
    });

    console.log("\n✅ setGovKeyWithGovKey called successfully!");
    console.log("transaction hash", tx);
  } catch (error) {
    console.error("\n❌ Error calling setGovKeyWithGovKey:");
    console.error(error.message);
    throw error;
  }

  console.log("\n=== Migration complete ===\n");
};
