// Run by: yarn tronbox migrate --f 6 --to 6 --network nile

module.exports = async function (deployer, network, accounts) {
  console.log("\n=== TRX Transfer to Vault with Note ===");

  // Vault address (hex format)
  const vaultAddress = "41c34856cadd5524892907d8a34126053447740375"; // TTmmRfpKqsypGRQbMUcrJu9MMhudRh8FCk

  console.log("Vault address (hex):", vaultAddress);

  // Transfer amount (TRX has 6 decimals)
  const amount = "1000000"; // 1 TRX (6 decimals)

  // Raw bytes note to include in the transaction
  // Example: hex string representing arbitrary data
  const note =
    "0x010012121212121212121212121212121212121212120089010164000000f627b6285759e4fa9ca1214c31f6748afaad766c6ccf732256d0ecbe06e43a03000000000000000000000000000000000000000000016e00000070d0cd75a367987344a3896a18e1510e5429ca5e88357b6c2a2e306b3877380d000000"; // "This is a Chainflip TRX Vault Swap!" in hex

  console.log("\nTransfer parameters:");
  console.log("- To (Vault):", vaultAddress);
  console.log("- Amount:", amount, "(1 TRX)");
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

    // Build the TRX transfer transaction
    console.log("\nBuilding TRX transfer transaction...");

    // Create a native TRX transfer transaction
    let transaction = await currentTronWeb.transactionBuilder.sendTrx(
      vaultAddress,
      amount,
      fromAddress
    );

    console.log("transaction", transaction);

    // Check if transaction was created successfully
    if (!transaction) {
      throw new Error("Failed to create transaction");
    }

    // Add memo/note to the transaction using addUpdateData
    transaction = await currentTronWeb.transactionBuilder.addUpdateData(
      transaction,
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

    console.log("\n✅ TRX transfer completed successfully!");
    console.log("Transaction result:", broadcast);
    console.log(
      "Transaction ID:",
      broadcast.txid || broadcast.transaction?.txID
    );
    console.log("Amount transferred:", amount, "TRX to", vaultAddress);
    console.log("Note attached:", note);
  } catch (err) {
    console.error("\n❌ Error during TRX transfer:");
    console.error(err && err.message ? err.message : err);
    throw err;
  }

  console.log("\n=== Migration complete ===\n");
};

// TX example with random cf_parameters:
//  https://nile.tronscan.org/#/transaction/f3de44cca0c78890854a637c215e19490211c0ece6cf892fe759773b98dbf900
// TX example of a valid TRX Vault Swap without CCM
//  https://nile.tronscan.org/#/transaction/b8042280e6a813d65ad01a0555e1e9a9497bf69d012b58cdc5d925c21df35972
