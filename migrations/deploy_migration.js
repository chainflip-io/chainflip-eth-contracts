const VaultContract = artifacts.require("Vault");

module.exports = function (deployer) {
  deployer.deploy(VaultContract);
};
