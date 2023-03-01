from os import environ
from consts import *
from web3.auto import w3
from brownie import network, accounts


def deploy_initial_Chainflip_contracts(
    deployer, KeyManager, Vault, StakeManager, FLIP, *args
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
        parity = aggKey[0:2]
        x = aggKey[2:]
        parity = "00" if parity == "02" or parity == "00" else "01"
        aggKey = [int(x, 16), int(parity, 16)]
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

    # Deploy Key Manager contract
    cf.keyManager = deployer.deploy(KeyManager, aggKey, cf.gov, cf.communityKey)

    # Deploy Vault contract
    cf.vault = deployer.deploy(Vault, cf.keyManager)

    # Deploy Stake Manager contract
    cf.stakeManager = deployer.deploy(
        StakeManager,
        cf.keyManager,
        MIN_STAKE,
    )

    # Deploy FLIP contract. Minting genesis validator FLIP to the Stake Manager.
    # The rest of genesis FLIP will be minted to the governance address for safekeeping.
    cf.flip = deployer.deploy(
        FLIP,
        INIT_SUPPLY,
        cf.numGenesisValidators,
        cf.genesisStake,
        cf.stakeManager.address,
        cf.gov,
        cf.keyManager,
    )

    cf.stakeManager.setFlip(cf.flip.address, {"from": deployer})

    # All the deployer rights and tokens have been delegated to the governance key.
    cf.safekeeper = cf.gov
    cf.deployer = deployer

    return cf


# This should be used over deploy_initial_Chainflip_contracts for actual deployments
def deploy_set_Chainflip_contracts(
    deployer, KeyManager, Vault, StakeManager, FLIP, *args
):
    cf = deploy_initial_Chainflip_contracts(
        deployer, KeyManager, Vault, StakeManager, FLIP, *args
    )
    cf.whitelisted = [cf.vault.address, cf.stakeManager.address, cf.flip.address]
    cf.keyManager.setCanConsumeKeyNonce(cf.whitelisted, {"from": cf.deployer})

    return cf


# Deploy USDC mimic token (standard ERC20) and transfer init amount to several accounts.
def deploy_usdc_contract(deployer, MockUSDC, accounts):

    mockUsdc = deployer.deploy(MockUSDC, "USD Coin", "USDC", INIT_USDC_SUPPLY)
    # Distribute tokens to other accounts
    for account in accounts:
        if account != deployer and mockUsdc.balanceOf(deployer) >= INIT_USDC_ACCOUNT:
            mockUsdc.transfer(account, INIT_USDC_ACCOUNT, {"from": deployer})

    return mockUsdc
