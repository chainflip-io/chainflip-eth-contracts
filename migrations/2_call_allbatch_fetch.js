// Run by: yarn tronbox migrate --f 2 --to 2 --network nile

const VaultContract = artifacts.require("Vault");

module.exports = async function (deployer, network, accounts) {
  console.log("\n=== Calling allBatch on existing Vault ===");

  // Load the existing Vault contract at the deployed address
  // Convert base58 address to hex format for web3/tronweb
  const vaultAddress = "41adeecfa46eb3579c0f733085ba69a296ae9ee743"; // TRpsz8cDtcH3oQGAdm19My5EGgTtw2cN5A

  console.log("Loading Vault at address:", vaultAddress);
  const vault = await VaultContract.at(vaultAddress);

  console.log("Vault loaded successfully!");
  console.log("Vault address (hex):", vault.address);

  // Prepare parameters for allBatch call
  // allBatch(deployFetchParamsArray, fetchParamsArray, transferParamsArray)

  // DeployFetchParams struct: (bytes32 swapID, address token)
  // Pass as array: [swapID, token]
  //   const deployFetchParamsArray = []

  // NATIVE
  // const deployFetchParamsArray = [
  //   [
  //     "0x0000000000000000000000000000000000000000000000000000000000000000", // swapID: bytes32 zero
  //     "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", // token: native token address
  //   ],
  // ];
  // USDT: 0x41eca9bc828a3005b9a3b909f2cc5c2a54794de05f107f6d36
  // 20-byte address: 0xeca9bc828a3005b9a3b909f2cc5c2a54794de05f
  const deployFetchParamsArray = [
    [
      "0x0000000000000000000000000000000000000000000000000000000000000000", // swapID: bytes32 zero
      "0xeca9bc828a3005b9a3b909f2cc5c2a54794de05f", // USDT
    ],
  ];
  const fetchParamsArray = [];
  const transferParamsArray = [];

  console.log("\nCalling allBatch with parameters:");
  console.log(
    "- deployFetchParamsArray:",
    deployFetchParamsArray.length,
    "items"
  );
  console.log("- fetchParamsArray:", fetchParamsArray.length, "items");
  console.log("- transferParamsArray:", transferParamsArray.length, "items");

  try {
    // Call allBatch - this will execute the transaction
    const tx = await vault.allBatch(
      deployFetchParamsArray,
      fetchParamsArray,
      transferParamsArray,
      {
        from: deployer.options.options.network_config.from,
      }
    );

    // This is not getting the tx has correctly, it's just undefined
    // byt the tx is sent.
    console.log("\n✅ allBatch called successfully!");
    console.log("Transaction hash:", tx.tx || tx.transactionHash);
    console.log("Gas used:", tx.receipt ? tx.receipt.gasUsed : "N/A");

    // Log any events emitted (if available)
    if (tx.logs && tx.logs.length > 0) {
      console.log("\nEvents emitted:");
      tx.logs.forEach((log, index) => {
        console.log(`  ${index + 1}. ${log.event}`);
      });
    }
  } catch (error) {
    console.error("\n❌ Error calling allBatch:");
    console.error(error.message);
    throw error;
  }

  console.log("\n=== Migration complete ===\n");
};

// ***** NATIVE FETCH! *****
// Example tx sent: https://nile.tronscan.org/#/transaction/7ad4d54e4fac3515e1e803209e95bcff915e201010fb0dd38bf06473845a95f3
// VaultAddress = "41adeecfa46eb3579c0f733085ba69a296ae9ee743"; // TRpsz8cDtcH3oQGAdm19My5EGgTtw2cN5A
// deployed Deposit contract at: TVTF9dvzB4Hqo9qtv2ZMiAMHqXYtpKURaK
// https://nile.tronscan.org/#/address/TVTF9dvzB4Hqo9qtv2ZMiAMHqXYtpKURaK
// Deposit fetch emitted address: TVTF9dvzB4Hqo9qtv2ZMiAMHqXYtpKURaK
// deployed Deposit contract hex: 0x41d5b7d46e0266a92af97ef45befa21991878a1675

// ***** USDT FETCH! *****
// USDT Address testnet: https://nile.tronscan.org/#/token20/TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf
// Hex: 0x41eca9bc828a3005b9a3b909f2cc5c2a54794de05f107f6d36
// 20-byte address: 0xeca9bc828a3005b9a3b909f2cc5c2a54794de05f
// TX: https://nile.tronscan.org/#/transaction/c2bfb35047f5b69a3c4721fb6bd5c5ab40e7273faa255080d442a79f1a0c1584
// Created deposit contract: TKfZUffqnAg5SqxwQwUG2vyvbSVLjMgkyn

// TODO: Try deposit native with a wallet and see if it correctly funnels it to the vault (native deployed deposit TVTF9dvzB4Hqo9qtv2ZMiAMHqXYtpKURaK)
// TODO: Try egressing both native and USDT tokens to check it works.
// TODO: Ensure actual fetching of funds work (>0), but we need precompute for that.
