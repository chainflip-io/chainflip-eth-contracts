from os import environ
from consts import *
from web3.auto import w3
from brownie import network, accounts


def deploy_Chainflip_contracts(
    deployer, KeyManager, Vault, StakeManager, FLIP, DeployerContract, *args
):

    # Set the priority fee for all transactions
    network.priority_fee("1 gwei")

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

    # Deploy contracts via cf.deployerContract. Minting genesis validator FLIP to the Stake Manager.
    # The rest of genesis FLIP will be minted to the governance address for safekeeping. Adding
    # required confirmations to avoid errors when checking contracts.address
    cf.deployerContract = DeployerContract.deploy(
        aggKey,
        cf.gov,
        cf.communityKey,
        MIN_STAKE,
        INIT_SUPPLY,
        cf.numGenesisValidators,
        cf.genesisStake,
        {"from": deployer, "required_confs": 1},
    )

    cf.vault = Vault.at(cf.deployerContract.vault())
    cf.flip = FLIP.at(cf.deployerContract.flip())
    cf.keyManager = KeyManager.at(cf.deployerContract.keyManager())
    cf.stakeManager = StakeManager.at(cf.deployerContract.stakeManager())

    # All the deployer rights and tokens have been delegated to the governance key.
    cf.safekeeper = cf.gov
    cf.deployer = deployer

    return cf


def deploy_new_vault(deployer, Vault, KeyManager, keyManager_address):
    # Set the priority fee for all transactions
    network.priority_fee("1 gwei")

    keyManager = KeyManager.at(keyManager_address)
    vault = Vault.deploy(keyManager, {"from": deployer, "required_confs": 1})

    return vault


def deploy_new_stakeManager(
    deployer,
    KeyManager,
    StakeManager,
    FLIP,
    DeployerStakeManager,
    keyManager_address,
    flip_address,
):
    # Set the priority fee for all transactions
    network.priority_fee("1 gwei")

    # TODO: We probably don't need this check, we should just deploy a new StakeManager.
    # Minimal check to ensure that at least the two contracts provided are the correct.
    # flip = FLIP.at(flip_address)
    # keyManager = KeyManager.at(keyManager_address)

    deployerStakeManager = DeployerStakeManager.deploy(
        MIN_STAKE,
        keyManager_address,
        flip_address,
        {"from": deployer, "required_confs": 1},
    )

    # New upgraded contracts
    stakeManager = StakeManager.at(deployerStakeManager.stakeManager())

    return (deployerStakeManager, stakeManager)


# Deploy USDC mimic token (standard ERC20) and transfer init amount to several accounts.
def deploy_usdc_contract(deployer, MockUSDC, accounts):

    mockUsdc = deployer.deploy(MockUSDC, "USD Coin", "USDC", INIT_USDC_SUPPLY)
    # Distribute tokens to other accounts
    for account in accounts:
        if account != deployer and mockUsdc.balanceOf(deployer) >= INIT_USDC_ACCOUNT:
            mockUsdc.transfer(account, INIT_USDC_ACCOUNT, {"from": deployer})

    return mockUsdc
