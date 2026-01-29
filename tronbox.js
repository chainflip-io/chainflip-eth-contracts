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
    mainnet: {
      privateKey: process.env.PRIVATE_KEY,
      feeLimit: 1e8,
      fullHost: "https://api.trongrid.io", // ⚠️ TRON mainnet endpoint
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
