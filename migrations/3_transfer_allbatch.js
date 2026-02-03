// yarn tronbox migrate --f 3 --to 3 --network nile

const VaultContract = artifacts.require("Vault");

module.exports = async function (deployer, network, accounts) {
  console.log("\n=== Calling allBatch on existing Vault (transfer only) ===");

  // Load the existing Vault contract at the deployed address
  // Convert base58 address to hex format for web3/tronweb
  const vaultAddress = "41adeecfa46eb3579c0f733085ba69a296ae9ee743"; // TRpsz8cDtcH3oQGAdm19My5EGgTtw2cN5A

  console.log("Loading Vault at address:", vaultAddress);
  const vault = await VaultContract.at(vaultAddress);

  // Amount: 1 TRX. On Nile/testnet examples use 1_000_000 (6 decimals)
  const amount = "1000000"; // 1 TRX
  // const recipient = "0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97";
  const recipient = "THQQYhjsNHUQva3E6YNogX4CWbBmV8qzoB";

  const deployFetchParamsArray = [];
  const fetchParamsArray = [];
  const transferParamsArray = [
    // pass as tuple: [token, recipient, amount]
    ["0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", recipient, amount],
  ];

  console.log("\nCalling allBatch with parameters:");
  console.log(
    "- deployFetchParamsArray:",
    deployFetchParamsArray.length,
    "items"
  );
  console.log("- fetchParamsArray:", fetchParamsArray.length, "items");
  console.log("- transferParamsArray:", transferParamsArray.length, "items");
  console.log("- transfer recipient:", recipient);
  console.log("- transfer amount:", amount);

  try {
    const tx = await vault.allBatch(
      deployFetchParamsArray,
      fetchParamsArray,
      transferParamsArray,
      {
        from:
          deployer.options &&
          deployer.options.options &&
          deployer.options.options.network_config &&
          deployer.options.options.network_config.from,
      }
    );

    console.log("\n✅ allBatch (transfer) called successfully!");
    console.log("transaction hash", tx);
  } catch (err) {
    console.error("\n❌ Error calling allBatch transfer:");
    console.error(err && err.message ? err.message : err);
    throw err;
  }

  console.log("\n=== Migration complete ===\n");
};

// https://nile.tronscan.org/#/transaction/b433c95e3f3142fc2bff4ac6b9267faf7118428959aa1868f5ae1e48832d2182
// Transfer to: 0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97
// Transfer seems to work well to a random address.
