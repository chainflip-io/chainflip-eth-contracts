// Run by: yarn tronbox migrate --f 2 --to 2 --network nile
// Deployer: TCKygWnz919n1frEAnp2Uoa5VzCasLes12

const VaultContract = artifacts.require("Vault");

module.exports = async function (deployer, network, accounts) {
  console.log("\n=== Calling allBatch on existing Vault ===");
  const deployerAccount = deployer.options.options.network_config.from;

  // Load the existing Vault contract at the deployed address
  // Convert base58 address to hex format for web3/tronweb
  // const vaultAddress = "41adeecfa46eb3579c0f733085ba69a296ae9ee743"; // TRpsz8cDtcH3oQGAdm19My5EGgTtw2cN5A
  // const vaultAddress = "41260b17d1ad3bda79746db09f7675dee7b28d169b"; // TDSMy79DPk164ZtxEh2GqinTz3nfjkGqdi
  // const vaultAddress = "41c042d9449e5340a4a6e48f73622ee0b611e56ea6"; // TTVnpcuAZs6tEUT2TuC7fmadgLgcyM431v
  // const vaultAddress = "TMiYQL4FPjEYQ9KyqM37T1QmAnKzJTntic";
  const vaultAddress = "TZEQtGkPWPFLSXQyEiQCJZQnzRpxCVb5zT";

  console.log("Loading Vault at address:", vaultAddress);
  const vault = await VaultContract.at(vaultAddress);

  console.log("Vault loaded successfully!");
  console.log("Vault address (hex):", vault.address);

  // Prepare parameters for allBatch call
  // allBatch(deployFetchParamsArray, fetchParamsArray, transferParamsArray)

  // DeployFetchParams struct: (bytes32 swapID, address token)
  // Pass as array: [swapID, token]
  const deployFetchParamsArray = [];

  // NATIVE
  // const deployFetchParamsArray = [];
  // const deployFetchParamsArray = [
  //   [
  //     "0x0000000000000000000000000000000000000000000000000000000000000000", // swapID: bytes32 zero
  //     "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", // token: native token address
  //   ],
  // ];
  // const fetchParamsArray = [
  //   [
  //     "TYQn89aNzAkwcCmTyKB3XPQJvbCn82Ew2y", // Deposit contract address
  //     "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", // TRX
  //   ],
  // ];
  // const transferParamsArray = [
  //   [
  //     "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", // token
  //     "TXhTQ2g2NsyrmVXyZJLbLscwNftHixDm2x", //recipient,
  //     2, // amount],
  //   ],
  // ];
  // USDT: 0x41eca9bc828a3005b9a3b909f2cc5c2a54794de05f107f6d36
  // 20-byte address: 0xeca9bc828a3005b9a3b909f2cc5c2a54794de05f
  // const deployFetchParamsArray = [
  //   [
  //     "0x0000000000000000000000000000000000000000000000000000000000000000", // swapID: bytes32 zero
  //     "0xeca9bc828a3005b9a3b909f2cc5c2a54794de05f", // USDT
  //   ],
  // ];
  // const fetchParamsArray = [
  //   [
  //     "TYQn89aNzAkwcCmTyKB3XPQJvbCn82Ew2y", // Deposit contract address
  //     "0xeca9bc828a3005b9a3b909f2cc5c2a54794de05f", // USDT
  //   ],
  // ];
  const transferParamsArray = [
    [
      "0xeca9bc828a3005b9a3b909f2cc5c2a54794de05f", // token (USDT)
      "TGAunhJqpXGrRgZib56anzUxvmpU665H7c", //recipient,
      2, // amount],
    ],
  ];
  const fetchParamsArray = [];
  // const transferParamsArray = [];

  console.log("\nCalling allBatch with parameters:");
  console.log(
    "- deployFetchParamsArray:",
    deployFetchParamsArray.length,
    "items"
  );
  console.log("- fetchParamsArray:", fetchParamsArray.length, "items");
  console.log("- transferParamsArray:", transferParamsArray.length, "items");
  // Using a random number to make it unlikely that it's a used nonce.
  const nonce = Math.floor(Math.random() * Number.MAX_SAFE_INTEGER);
  try {
    // Call allBatch - this will execute the transaction
    const tx = await vault.allBatch(
      [1, nonce, deployerAccount],
      deployFetchParamsArray,
      fetchParamsArray,
      transferParamsArray,
      {
        from: deployerAccount,
      }
    );

    // This is not getting the tx has correctly, it's just undefined
    // byt the tx is sent.
    console.log("\n✅ allBatch called successfully!");
    console.log("transaction hash", tx);
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
