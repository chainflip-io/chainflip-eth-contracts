
// Settings created to get a realistic chain that mines blocks periodically. Requested by the CFE team.
module.exports = {
    networks: {
        hardhat: {
            hardfork: "shanghai",
            // base fee of 0 allows use of 0 gas price when testing
            initialBaseFeePerGas: 1000000000,
            // brownie expects calls and transactions to throw on revert
            throwOnTransactionFailures: true,
            throwOnCallFailures: true,
            mining: {
                auto: false,
                // Do not go lower than this - it causes the hardhat node to eventually only mine
                // empty blocks and not include any transactions.
                interval: 1500
            }
        }
    }
}