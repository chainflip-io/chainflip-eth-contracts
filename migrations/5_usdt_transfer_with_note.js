// Run by: yarn tronbox migrate --f 5 --to 5 --network nile

module.exports = async function (deployer, network, accounts) {
  console.log("\n=== USDT Transfer to Vault with Note ===");

  // Vault address (hex format)
  const vaultAddress = "41c34856cadd5524892907d8a34126053447740375"; // TTmmRfpKqsypGRQbMUcrJu9MMhudRh8FCk

  // USDT token address on Tron Nile testnet
  const usdtAddress = "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"; // Replace with actual USDT address if different

  console.log("Vault address (hex):", vaultAddress);
  console.log("USDT token address:", usdtAddress);

  // Transfer amount (adjust based on USDT decimals, typically 6 decimals)
  const amount = "1000000"; // 1 USDT (6 decimals)

  // Raw bytes note to include in the transaction
  // Example: hex string representing arbitrary data
  const note = "0x48656c6c6f20436861696e666c69702100"; // "Hello Chainflip!" in hex

  console.log("\nTransfer parameters:");
  console.log("- To (Vault):", vaultAddress);
  console.log("- Amount:", amount, "(1 USDT)");
  console.log("- Note (raw bytes):", note);

  const fromAddress =
    deployer.options &&
    deployer.options.options &&
    deployer.options.options.network_config &&
    deployer.options.options.network_config.from;

  console.log("- From address:", fromAddress);

  try {
    const currentTronWeb = tronWeb;

    // Convert note to hex string without 0x prefix
    const noteHex = note.startsWith("0x") ? note.substring(2) : note;

    // First, build the transfer transaction
    console.log("\nBuilding transfer transaction...");
    const parameter = [
      { type: "address", value: vaultAddress },
      { type: "uint256", value: amount },
    ];

    const options = {
      feeLimit: 100000000, // 100 TRX fee limit
      callValue: 0,
    };

    // Create the transaction with transfer function
    let transaction =
      await currentTronWeb.transactionBuilder.triggerSmartContract(
        currentTronWeb.address.toHex(usdtAddress),
        "transfer(address,uint256)",
        options,
        parameter,
        currentTronWeb.address.toHex(fromAddress)
      );
    console.log("transaction", transaction);

    // Check if transaction was created successfully
    if (!transaction || !transaction.transaction) {
      throw new Error("Failed to create transaction");
    }

    // Add memo/note to the transaction using addUpdateData
    transaction = await currentTronWeb.transactionBuilder.addUpdateData(
      transaction.transaction,
      noteHex,
      "hex"
    );

    console.log("Note attached to transaction:", note);
    console.log("Updated transaction:", transaction);

    // Sign the transaction (this will include the note in the signature)
    console.log("\nSigning transaction...");
    const signedTx = await currentTronWeb.trx.sign(
      transaction,
      currentTronWeb.defaultPrivateKey
    );

    // Broadcast the signed transaction
    console.log("Broadcasting transaction...");
    const broadcast = await currentTronWeb.trx.sendRawTransaction(signedTx);

    console.log("\n✅ USDT transfer completed successfully!");
    console.log("Transaction result:", broadcast);
    console.log(
      "Transaction ID:",
      broadcast.txid || broadcast.transaction?.txID
    );
    console.log("Amount transferred:", amount, "to", vaultAddress);
    console.log("Note attached:", note);
  } catch (err) {
    console.error("\n❌ Error during USDT transfer:");
    console.error(err && err.message ? err.message : err);
    throw err;
  }

  console.log("\n=== Migration complete ===\n");
};

// Example with added message
// https://nile.tronscan.org/#/transaction/7a89015e99a64e1731efe6da8ae705384a51592e38e715a0b045809b62ccd31d
