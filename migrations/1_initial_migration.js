// We need to use --reset for the migration run to work.
// yarn tronbox migrate --f 1 --to 1 --reset --network nile

const VaultContract = artifacts.require("Vault");
const KeyManagerContract = artifacts.require("KeyManager");

module.exports = async function (deployer) {
  console.log("Starting deployment of VaultContract...");
  const deployerAccount = deployer.options.options.network_config.from;
  console.log("Using deployer account:", deployerAccount); // TCKygWnz919n1frEAnp2Uoa5VzCasLes12
  await deployer.deploy(
    KeyManagerContract,
    [1, 2], // dummy aggKey
    deployerAccount,
    deployerAccount
  );

  const keyManagerInstance = await KeyManagerContract.deployed();
  const keyManagerAddress = keyManagerInstance.address;
  console.log("KeyManagerContract deployed at address:", keyManagerAddress);

  // deploy a contract
  await deployer.deploy(VaultContract, keyManagerAddress);
  //access information about your deployed contract instance
  const instance = await VaultContract.deployed();
  console.log("VaultContract deployed at address:", instance.address); // 0x4132aea965af223ab8831b58ab2b8b80136856d53e
  // Contract deployed: TEbC2Mm2razM2LsE7CJQUho9yn3z7zujLc
  // Deployment tx: https://nile.tronscan.org/#/transaction/08e95ceeb3f1f60844336e1ee80764ddfbd759ab77cff4806099b7d1c6799544

  // Call getDepositBytecode and print the result
  // Added view function in the Vault contract
  // function getDepositBytecode() external pure returns (bytes memory) {
  //     return type(Deposit).creationCode;
  // }
  // console.log("\nCalling getDepositBytecode()...");
  // const depositBytecode = await instance.getDepositBytecode();
  // console.log("Deposit contract bytecode:");
  // console.log(depositBytecode);
  // console.log("Bytecode length:", depositBytecode.length);
};

//// DEPLOYED WITH RECEIVE
// https://nile.tronscan.org/#/transaction/bfbec1a55fb4f6b4fb630dd1307a92ed9488d6ac25b90da54f1d9082f8440d28
// Using deployer account: TCKygWnz919n1frEAnp2Uoa5VzCasLes12
//   Deploying Vault...
//   Vault:
//     (base58) TRpsz8cDtcH3oQGAdm19My5EGgTtw2cN5A
//     (hex) 41adeecfa46eb3579c0f733085ba69a296ae9ee743
// VaultContract deployed at address: 41adeecfa46eb3579c0f733085ba69a296ae9ee743

// Calling getDepositBytecode()...
// Deposit contract bytecode:
// 0x60a060405234801561001057600080fd5b50d3801561001d57600080fd5b50d2801561002a57600080fd5b506040516104ae3803806104ae833981016040819052610049916101a3565b336080526001600160a01b03811673eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee036100cc57604051600090339047908381818185875af1925050503d80600081146100b3576040519150601f19603f3d011682016040523d82523d6000602084013e6100b8565b606091505b50509050806100c657600080fd5b5061019d565b6040516370a0823160e01b81523060048201526001600160a01b0382169063a9059cbb90339083906370a0823190602401602060405180830381865afa15801561011a573d6000803e3d6000fd5b505050506040513d601f19601f8201168201806040525081019061013e91906101dc565b6040516001600160e01b031960e085901b1681526001600160a01b0390921660048301526024820152604401600060405180830381600087803b15801561018457600080fd5b505af1158015610198573d6000803e3d6000fd5b505050505b506101f5565b6000602082840312156101b557600080fd5b81516001600160a81b03811681146101cc57600080fd5b6001600160a01b03169392505050565b6000602082840312156101ee57600080fd5b5051919050565b60805161029961021560003960008181602b015260ee01526102996000f3fe6080604052600436106100225760003560e01c8063f109a0be146100ae57600080fd5b366100a95760007f00000000000000000000000000000000000000000000000000000000000000006001600160a01b03164760405160006040518083038185875af1925050503d8060008114610094576040519150601f19603f3d011682016040523d82523d6000602084013e610099565b606091505b50509050806100a757600080fd5b005b600080fd5b3480156100ba57600080fd5b50d380156100c757600080fd5b50d280156100d457600080fd5b506100a76100e3366004610203565b336001600160a01b037f0000000000000000000000000000000000000000000000000000000000000000161461011857600080fd5b6040516370a0823160e01b81523060048201526001600160a01b0382169063a9059cbb90339083906370a0823190602401602060405180830381865afa158015610166573d6000803e3d6000fd5b505050506040513d601f19601f8201168201806040525081019061018a919061024a565b6040517fffffffff0000000000000000000000000000000000000000000000000000000060e085901b1681526001600160a01b0390921660048301526024820152604401600060405180830381600087803b1580156101e857600080fd5b505af11580156101fc573d6000803e3d6000fd5b5050505050565b60006020828403121561021557600080fd5b813574ffffffffffffffffffffffffffffffffffffffffff8116811461023a57600080fd5b6001600160a01b03169392505050565b60006020828403121561025c57600080fd5b505191905056fea26474726f6e58221220b97657d8cc1470c28dcb1d8e96a321a926c06d32909e7ccd033409e6c31fac6464736f6c63430008140033
// Bytecode length: 2398
// This bytecode matches the build/contracts/Deposit.json "bytecode"

//// DEPLOYED WITH FALLBACK

// Running migration: 1_initial_migration.js
// Starting deployment of VaultContract...
// Using deployer account: TCKygWnz919n1frEAnp2Uoa5VzCasLes12
//   Deploying Vault...
//   Vault:
//     (base58) TDSMy79DPk164ZtxEh2GqinTz3nfjkGqdi
//     (hex) 41260b17d1ad3bda79746db09f7675dee7b28d169b
// VaultContract deployed at address: 41260b17d1ad3bda79746db09f7675dee7b28d169b
// https://nile.tronscan.org/#/contract/TDSMy79DPk164ZtxEh2GqinTz3nfjkGqdi/code
