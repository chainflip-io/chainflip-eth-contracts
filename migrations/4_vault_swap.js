// Run by: yarn tronbox migrate --f 4 --to 4 --network nile

const VaultContract = artifacts.require("Vault");
const TRC20Contract = artifacts.require("ERC20");

module.exports = async function (deployer, network, accounts) {
  console.log("\n=== Calling xSwapToken on existing Vault ===");

  // Load the existing Vault contract at the deployed address
  // Convert base58 address to hex format for web3/tronweb
  const vaultAddress = "41c34856cadd5524892907d8a34126053447740375"; // TTmmRfpKqsypGRQbMUcrJu9MMhudRh8FCk

  console.log("Loading Vault at address:", vaultAddress);
  const vault = await VaultContract.at(vaultAddress);

  console.log("Vault loaded successfully!");
  console.log("Vault address (hex):", vault.address);

  // Prepare parameters for xSwapToken call
  // xSwapToken(uint32 dstChain, bytes memory dstAddress, uint32 dstToken, IERC20 srcToken, uint256 amount, bytes calldata cfParameters)

  const dstChain = 1; // Destination chain ID (example value)
  const dstAddress = "0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97"; // Destination address on target chain
  const dstToken = 1; // Destination token ID (example value)
  const srcTokenAddress = "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"; // Source token address
  const cfParameters = "0x"; // Additional Chainflip parameters (empty bytes)

  // Amount of tokens to swap (adjust based on token decimals)
  const amount = "1"; // 1 token

  console.log("\nLoading source token contract...");
  const srcToken = await TRC20Contract.at(srcTokenAddress);
  console.log("Source token loaded:", srcTokenAddress);

  const fromAddress =
    deployer.options &&
    deployer.options.options &&
    deployer.options.options.network_config &&
    deployer.options.options.network_config.from;

  console.log("\nApproving Vault to spend tokens...");
  const approveTx = await srcToken.approve(vault.address, amount, {
    from: fromAddress,
  });
  console.log("Approval transaction:", approveTx);

  console.log("\nCalling xSwapToken with parameters:");
  console.log("- dstChain:", dstChain);
  console.log("- dstAddress:", dstAddress);
  console.log("- dstToken:", dstToken);
  console.log("- srcToken:", srcTokenAddress);
  console.log("- amount:", amount);
  console.log("- cfParameters:", cfParameters);

  try {
    const tx = await vault.xSwapToken(
      dstChain,
      dstAddress,
      dstToken,
      srcTokenAddress,
      amount,
      cfParameters,
      {
        from: fromAddress,
      }
    );

    console.log("\n✅ xSwapToken called successfully!");
    console.log("Transaction hash:", tx);
  } catch (err) {
    console.error("\n❌ Error calling xSwapToken:");
    console.error(err && err.message ? err.message : err);
    throw err;
  }

  console.log("\n=== Migration complete ===\n");
};
