from os import environ
from consts import *
from web3.auto import w3
from brownie import network, accounts, chain


def deploy_Chainflip_contracts(
    deployer,
    KeyManager,
    Vault,
    StateChainGateway,
    FLIP,
    DeployerContract,
    AddressChecker,
    *args,
):

    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    class Context:
        pass

    cf = Context()

    environment = {}
    if args:
        environment = args[0]

    # NOTE: When deploying to a live network (via deploy_contracts.py) the environment
    # variables are forced to be set by the user to avoid defaulting to the testnet values.
    # Therefore, the default values for env. variables in this script are only used in testing.

    aggKey = environment.get("AGG_KEY")
    if aggKey:
        aggKey = getKeysFromAggKey(aggKey)
    else:
        aggKey = AGG_SIGNER_1.getPubData()

    govKey = environment.get("GOV_KEY")
    if govKey:
        cf.gov = govKey
    else:
        cf.gov = accounts[0]

    communityKey = environment.get("COMM_KEY")
    if communityKey:
        cf.communityKey = communityKey
    else:
        cf.communityKey = accounts[6]

    cf.numGenesisValidators = int(
        environment.get("NUM_GENESIS_VALIDATORS") or NUM_GENESIS_VALIDATORS
    )

    cf.genesisStake = int(environment.get("GENESIS_STAKE") or GENESIS_STAKE)

    print(
        f"Deploying with AGG_KEY: {aggKey}, GOV_KEY: {cf.gov} and COMM_KEY: {cf.communityKey}"
    )
    print(
        f"Deploying with NUM_GENESIS_VALIDATORS: {cf.numGenesisValidators}, GENESIS_STAKE: {cf.genesisStake}"
    )

    # Deploy contracts via cf.deployerContract. Minting genesis validator FLIP to the State Chain Gateway.
    # The rest of genesis FLIP will be minted to the governance address for safekeeping.
    cf.deployerContract = DeployerContract.deploy(
        aggKey,
        cf.gov,
        cf.communityKey,
        MIN_FUNDING,
        INIT_SUPPLY,
        cf.numGenesisValidators,
        cf.genesisStake,
        {"from": deployer, "required_confs": required_confs},
    )
    cf.addressChecker = AddressChecker.deploy(
        {"from": deployer, "required_confs": required_confs}
    )

    cf.vault = Vault.at(cf.deployerContract.vault())
    cf.flip = FLIP.at(cf.deployerContract.flip())
    cf.keyManager = KeyManager.at(cf.deployerContract.keyManager())
    cf.stateChainGateway = StateChainGateway.at(cf.deployerContract.stateChainGateway())

    # All the deployer rights and tokens have been delegated to the governance key.
    cf.safekeeper = cf.gov
    cf.deployer = deployer

    return cf


def deploy_new_vault(deployer, Vault, KeyManager, keyManager_address):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    keyManager = KeyManager.at(keyManager_address)
    vault = Vault.deploy(
        keyManager, {"from": deployer, "required_confs": required_confs}
    )

    return vault


def deploy_new_stateChainGateway(
    deployer,
    KeyManager,
    StateChainGateway,
    FLIP,
    DeployerStateChainGateway,
    keyManager_address,
    flip_address,
    min_funding,
):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    flip = FLIP.at(flip_address)
    keyManager = KeyManager.at(keyManager_address)

    deployerStateChainGateway = DeployerStateChainGateway.deploy(
        min_funding,
        keyManager.address,
        flip.address,
        {"from": deployer, "required_confs": required_confs},
    )

    # New upgraded contract
    stateChainGateway = StateChainGateway.at(
        deployerStateChainGateway.stateChainGateway()
    )

    return (deployerStateChainGateway, stateChainGateway)


def deploy_new_keyManager(deployer, KeyManager, aggKey, govKey, communityKey):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    # Deploy a new KeyManager
    keyManager = KeyManager.deploy(
        aggKey,
        govKey,
        communityKey,
        {"from": deployer, "required_confs": required_confs},
    )

    return keyManager


def deploy_new_multicall(deployer, Multicall, vault_address):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    # Deploy a new Multicall
    multicall = Multicall.deploy(
        vault_address,
        {"from": deployer, "required_confs": required_confs},
    )

    return multicall


# Deploy USDC mimic token (standard ERC20) and transfer init amount to several accounts.
def deploy_usdc_contract(deployer, MockUSDC, accounts):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    mockUsdc = MockUSDC.deploy(
        "USD Coin",
        "USDC",
        INIT_USDC_SUPPLY,
        {"from": deployer, "required_confs": required_confs},
    )
    # Distribute tokens to other accounts
    for account in accounts:
        if account != deployer and mockUsdc.balanceOf(deployer) >= INIT_USDC_ACCOUNT:
            mockUsdc.transfer(account, INIT_USDC_ACCOUNT, {"from": deployer})

    return mockUsdc


def deploy_addressHolder(
    deployer,
    AddressHolder,
    governor,
    stateChainGateway_address,
    stMinter_address,
    stBurner_address,
    stFLIP_address,
):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    addressHolder = AddressHolder.deploy(
        governor,
        stateChainGateway_address,
        stMinter_address,
        stBurner_address,
        stFLIP_address,
        {"from": deployer, "required_confs": required_confs},
    )

    return addressHolder


def deploy_tokenVestingNoStaking(
    deployer,
    TokenVestingNoStaking,
    beneficiary,
    revoker,
    cliff,
    end,
    transferableBeneficiary,
    flip,
    amount,
):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    tokenVestingNoStaking = TokenVestingNoStaking.deploy(
        beneficiary,
        revoker,
        cliff,
        end,
        transferableBeneficiary,
        {"from": deployer, "required_confs": required_confs},
    )

    flip.transfer(tokenVestingNoStaking.address, amount, {"from": deployer})

    return tokenVestingNoStaking


def deploy_tokenVestingStaking(
    deployer,
    TokenVestingStaking,
    beneficiary,
    revoker,
    end,
    transferableBeneficiary,
    addressHolder_address,
    flip,
    amount,
):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    tokenVestingStaking = TokenVestingStaking.deploy(
        beneficiary,
        revoker,
        end,
        transferableBeneficiary,
        addressHolder_address,
        flip.address,
        {"from": deployer, "required_confs": required_confs},
    )

    flip.transfer(tokenVestingStaking.address, amount, {"from": deployer})

    return tokenVestingStaking


# Deploying in live networks sometimes throws an error when getting the address of the deployed contract.
# I suspect that the RPC nodes might not have processed the transaction. Increasing the required confirmations
# to more than one is a problem in local networks with hardhat's automining enabled, as it will brick
# the script. Therefore, we increase the required_confs for live networks only. No need to do it for testing
# nor localnets/devnets - that is with hardhat (including forks), with id 31337, and geth image, with id 10997.
def transaction_params():
    network.priority_fee("1 gwei")
    return 1 if (chain.id == 31337 or chain.id == 10997) else 4
