// TODO: We probably want to set the  userFeePercentage and originEnergyLimit on e per contract
// deployment instead to only cover Vault calls.
// e.g. deployer.deploy(MyContract, { feeLimit: 1000000000, callValue: 0,  originEnergyLimit: 10000000});
module.exports = {
  networks: {
    development: {
      // For tronbox/tre docker image
      // See https://hub.docker.com/r/tronbox/tre
      privateKey:
        "0000000000000000000000000000000000000000000000000000000000000001",
      userFeePercentage: 0, // The percentage of resource consumption ratio.
      feeLimit: 1000 * 1e6, // The TRX consumption limit for the deployment and trigger, unit is SUN
      fullHost: "http://127.0.0.1:9090",
      network_id: "*",
      originEnergyLimit: 10_000_000, // Default origin energy limit for contract deployment
    },
    nile: {
      // Obtain test coin at https://nileex.io/join/getJoinPage
      privateKey: process.env.PRIVATE_KEY_NILE,
      // TO use mnenonic instead of private key:
      //   mnemonic: process.env.MNEMONIC,
      //   path: "m/44'/195'/0'/0/0",
      userFeePercentage: 20,
      feeLimit: 1000 * 1e6,
      fullHost: "https://nile.trongrid.io",
      network_id: "3",
      originEnergyLimit: 10_000_000, // Default origin energy limit for contract deployment
    },
    mainnet: {
      privateKey: process.env.PRIVATE_KEY,
      userFeePercentage: 0,
      feeLimit: 500 * 1e6, // 500 TRX
      fullHost: "https://api.trongrid.io",
      network_id: "1",
      originEnergyLimit: 10_000_000, // Default origin energy limit for contract deployment
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
