// TODO: We might want to set the  userFeePercentage and originEnergyLimit on a per contract
// deployment instead to only cover Vault calls, even though it shouldn't make a difference
// to have that for the KeyManager as well.
// e.g. deployer.deploy(MyContract, { feeLimit: 1000000000, callValue: 0,  originEnergyLimit: 10000000});
module.exports = {
  networks: {
    development: {
      // Also used by `tronbox test` for migrations (always runs against "development").
      // Points to the same java-tron node as localnet.
      privateKey:
        "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
      feeLimit: 1000 * 1e6, // The TRX consumption limit for the deployment and trigger, unit is SUN
      fullHost: "http://127.0.0.1:8090",
      network_id: "*",
      userFeePercentage: 5, // The percentage of resource consumption ratio.
      originEnergyLimit: 800_000,
    },
    localnet: {
      // For the chainflip localnet TRON node (tronprotocol/java-tron via ci/docker/tron/).
      // Deployer is Hardhat account #0 from the standard test mnemonic:
      //   EVM:  0xf39Fd6e51aad88F6f4ce6aB8827279cffFb92266
      //   TRON: TYBNgWfhGuNzdLtjKtxXTfskAhTbMcqbaG
      privateKey:
        "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
      feeLimit: 1000 * 1e6,
      fullHost: "http://127.0.0.1:8090",
      network_id: "*",
      userFeePercentage: 5,
      originEnergyLimit: 800_000,
    },
    nile: {
      privateKey: process.env.PRIVATE_KEY_NILE,
      // To use mnemonic instead of private key:
      //   mnemonic: process.env.MNEMONIC,
      //   path: "m/44'/195'/0'/0/0",
      userFeePercentage: 5,
      feeLimit: 1000 * 1e6,
      fullHost: "https://nile.trongrid.io",
      network_id: "3",
      originEnergyLimit: 800_000,
    },
    mainnet: {
      privateKey: process.env.PRIVATE_KEY,
      feeLimit: 500 * 1e6, // 500 TRX
      fullHost: "https://api.trongrid.io",
      network_id: "1",
      userFeePercentage: 5,
      originEnergyLimit: 800_000,
    },
  },
  compilers: {
    solc: {
      version: "0.8.20",
      settings: {
        optimizer: {
          enabled: true,
          runs: 800,
        },
        evmVersion: "istanbul",
        viaIR: false,
      },
    },
  },
};
