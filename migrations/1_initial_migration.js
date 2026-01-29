const VaultContract = artifacts.require("Vault");

module.exports = async function (deployer) {
  console.log("Starting deployment of VaultContract...");
  console.log(
    "Using deployer account:",
    deployer.options.options.network_config.from
  ); // TCKygWnz919n1frEAnp2Uoa5VzCasLes12
  const keyManagerAddress = "0xcd351d3626Dc244730796A3168D315168eBf08Be"; // TODO: To modify
  // deploy a contract
  await deployer.deploy(VaultContract, keyManagerAddress);
  //access information about your deployed contract instance
  const instance = await VaultContract.deployed();
  console.log("VaultContract deployed at address:", instance.address); // 0x4132aea965af223ab8831b58ab2b8b80136856d53e
  // Contract deployed: TEbC2Mm2razM2LsE7CJQUho9yn3z7zujLc
  // Deployment tx: https://nile.tronscan.org/#/transaction/08e95ceeb3f1f60844336e1ee80764ddfbd759ab77cff4806099b7d1c6799544
};
