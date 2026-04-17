// To run, move this file to the migrations/ folder as "2_set_agg_key_with_gov_key.js" and run:
// yarn tronbox migrate --f 2 --to 2 --network nile

const KeyManagerContract = artifacts.require("KeyManager");

module.exports = async function (deployer, network, accounts) {
  console.log("\n=== Calling setAggKeyWithGovKey on existing KeyManager ===");
  const deployerAccount = deployer.options.options.network_config.from;
  console.log("Using deployer account (govKey):", deployerAccount);

  // Load the existing KeyManager contract at the deployed address
  const keyManagerAddress = "TZEQtGkPWPFLSXQyEiQCJZQnzRpxCVb5zT";

  console.log("Loading KeyManager at address:", keyManagerAddress);
  const keyManager = await KeyManagerContract.at(keyManagerAddress);

  console.log("KeyManager loaded successfully!");
  console.log("KeyManager address (hex):", keyManager.address);

  // New aggregate key: Key struct (uint256 pubKeyX, uint8 pubKeyYParity)
  // Pass as tuple: [pubKeyX, pubKeyYParity]
  const newAggKey = [3, 0];

  console.log("\nCalling setAggKeyWithGovKey with parameters:");
  console.log("- newAggKey:", newAggKey);

  try {
    const tx = await keyManager.setAggKeyWithGovKey(newAggKey, {
      from: deployerAccount,
    });

    console.log("\n✅ setAggKeyWithGovKey called successfully!");
    console.log("transaction hash", tx);
  } catch (error) {
    console.error("\n❌ Error calling setAggKeyWithGovKey:");
    console.error(error.message);
    throw error;
  }

  console.log("\n=== Migration complete ===\n");
};
