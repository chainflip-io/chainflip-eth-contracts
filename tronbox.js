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
    },
    nile: {
      // Obtain test coin at https://nileex.io/join/getJoinPage
      privateKey: process.env.PRIVATE_KEY_NILE,
      // TO use mnenonic instead of private key:
      //   mnemonic: process.env.MNEMONIC,
      //   path: "m/44'/195'/0'/0/0",
      userFeePercentage: 100,
      feeLimit: 1000 * 1e6,
      fullHost: "https://nile.trongrid.io",
      network_id: "3",
    },
    mainnet: {
      privateKey: process.env.PRIVATE_KEY,
      userFeePercentage: 0,
      feeLimit: 500 * 1e6, // 500 TRX
      fullHost: "https://api.trongrid.io",
      network_id: "1",
    },
  },
  compilers: {
    solc: {
      version: "0.8.20",
      // An object with the same schema as the settings entry in the Input JSON.
      // See https://docs.soliditylang.org/en/latest/using-the-compiler.html#input-description
      settings: {
        optimizer: {
          enabled: true,
          runs: 800,
        },
        evmVersion: "paris",
        viaIR: false,
      },
    },
  },
};
