from os import environ
from consts import *
from web3.auto import w3
from brownie import network, accounts, chain


# NOTE: When deploying to a live network (via deploy_contracts.py) the environment
# variables are forced to be set by the user to avoid defaulting to the testnet values.
# Therefore, the default values for env. variables in this script are only used in testing.
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

    get_env_keys(cf, environment)

    cf.redemptionDelay = int(environment.get("REDEMPTION_DELAY") or REDEMPTION_DELAY)

    # Ensure it's either the mainnet or the testnet values
    assert cf.redemptionDelay in [REDEMPTION_DELAY, REDEMPTION_DELAY_TESTNETS]

    cf.numGenesisValidators = int(
        environment.get("NUM_GENESIS_VALIDATORS") or NUM_GENESIS_VALIDATORS
    )
    cf.genesisStake = int(environment.get("GENESIS_STAKE") or GENESIS_STAKE)

    print(
        f"Deploying with NUM_GENESIS_VALIDATORS: {cf.numGenesisValidators}, GENESIS_STAKE: {cf.genesisStake}"
    )

    # Deploy contracts via cf.deployerContract. Minting genesis validator FLIP to the State Chain Gateway.
    # The rest of genesis FLIP will be minted to the governance address for safekeeping.
    cf.deployerContract = DeployerContract.deploy(
        cf.aggKey,
        cf.gov,
        cf.communityKey,
        MIN_FUNDING,
        cf.redemptionDelay,
        INIT_SUPPLY,
        cf.numGenesisValidators,
        cf.genesisStake,
        {"from": deployer, "required_confs": required_confs},
    )
    cf.addressChecker = deploy_address_checker(deployer, AddressChecker)

    cf.vault = Vault.at(cf.deployerContract.vault())
    cf.flip = FLIP.at(cf.deployerContract.flip())
    cf.keyManager = KeyManager.at(cf.deployerContract.keyManager())
    cf.stateChainGateway = StateChainGateway.at(cf.deployerContract.stateChainGateway())

    # All the deployer rights and tokens have been delegated to the governance & safekeeper key.
    cf.safekeeper = cf.gov
    cf.deployer = deployer

    return cf


def deploy_contracts_secondary_evm(
    deployer,
    KeyManager,
    Vault,
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

    get_env_keys(cf, environment)

    cf.keyManager = deploy_new_keyManager(
        deployer, KeyManager, cf.aggKey, cf.gov, cf.communityKey
    )
    cf.vault = deploy_new_vault(deployer, Vault, KeyManager, cf.keyManager.address)

    cf.addressChecker = AddressChecker.deploy(
        {"from": deployer, "required_confs": required_confs}
    )

    cf.deployer = deployer

    return cf


def get_env_keys(cf, environment):
    aggKey = environment.get("AGG_KEY")
    if aggKey:
        cf.aggKey = getKeysFromAggKey(aggKey)
    else:
        cf.aggKey = AGG_SIGNER_1.getPubData()

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

    print(
        f"Deploying with AGG_KEY: {aggKey}, GOV_KEY: {cf.gov} and COMM_KEY: {cf.communityKey}"
    )


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
    redemption_delay,
):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    flip = FLIP.at(flip_address)
    keyManager = KeyManager.at(keyManager_address)

    deployerStateChainGateway = DeployerStateChainGateway.deploy(
        min_funding,
        redemption_delay,
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


def deploy_new_cfReceiver(deployer, cfReceiver, vault_address):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    # Deploy a new cfReceiver
    return cfReceiver.deploy(
        vault_address,
        {"from": deployer, "required_confs": required_confs},
    )


def deploy_scUtils(deployer, cfScUtils, stateChainGateway_address, vault_address):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    return cfScUtils.deploy(
        stateChainGateway_address,
        vault_address,
        {"from": deployer, "required_confs": required_confs},
    )


# Deploy USDC mock token and transfer init amount to several accounts.
def deploy_usdc_contract(deployer, MockUSDC, accounts):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    mockUsdc = MockUSDC.deploy(
        "USD Coin",
        "USDC",
        INIT_USD_SUPPLY,
        {"from": deployer, "required_confs": required_confs},
    )
    # Distribute tokens to other accounts
    for account in accounts:
        if account != deployer and mockUsdc.balanceOf(deployer) >= INIT_USD_BALANCE:
            mockUsdc.transfer(account, INIT_USD_BALANCE, {"from": deployer})

    return mockUsdc


# Deploy USDT mock token
def deploy_usdt_contract(deployer, MockUSDT, accounts):
    # Set the priority fee for all transactions and the required number of confirmations.
    required_confs = transaction_params()

    mockUsdt = MockUSDT.deploy(
        "Tether USD",
        "USDT",
        INIT_USD_SUPPLY,
        {"from": deployer, "required_confs": required_confs},
    )
    # Distribute tokens to other accounts
    for account in accounts:
        if account != deployer and mockUsdt.balanceOf(deployer) >= INIT_USD_BALANCE:
            mockUsdt.transfer(account, INIT_USD_BALANCE, {"from": deployer})

    return mockUsdt


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


def deploy_tokenVesting_andFund(flip, amount, deployer, staking, *args):
    fcn = deploy_tokenVestingStaking if staking else deploy_tokenVestingNoStaking
    tv = fcn(deployer, *args)

    flip.transfer(
        tv.address,
        amount,
        {"from": deployer},
    )
    return tv


def deploy_tokenVestingNoStaking(
    deployer,
    TokenVestingNoStaking,
    beneficiary,
    revoker,
    cliff,
    end,
    transferableBeneficiary,
):
    tokenVestingNoStaking = TokenVestingNoStaking.deploy(
        beneficiary,
        revoker,
        cliff,
        end,
        transferableBeneficiary,
        {"from": deployer},
    )
    return tokenVestingNoStaking


def deploy_tokenVestingStaking(
    deployer,
    TokenVestingStaking,
    beneficiary,
    revoker,
    start,
    end,
    transferableBeneficiary,
    addressHolder_address,
    flip,
):
    tokenVestingStaking = TokenVestingStaking.deploy(
        beneficiary,
        revoker,
        start,
        end,
        transferableBeneficiary,
        addressHolder_address,
        flip.address,
        {"from": deployer},
    )
    return tokenVestingStaking


def deploy_address_checker(deployer, AddressChecker):
    required_confs = transaction_params()

    addressChecker = AddressChecker.deploy(
        {"from": deployer, "required_confs": required_confs}
    )
    return addressChecker


def deploy_price_feeds(deployer, PriceFeedMockContract, feed_descriptions):
    required_confs = transaction_params()

    deployed_feeds = []

    for description in feed_descriptions:
        feed_contract = PriceFeedMockContract.deploy(
            8,  # decimals
            6,  # version
            description,
            {"from": deployer, "required_confs": required_confs},
        )
        deployed_feeds.append([description, feed_contract])

    return deployed_feeds


# Deploying in live networks sometimes throws an error when getting the address of the deployed contract.
# I suspect that the RPC nodes might not have processed the transaction. Increasing the required confirmations
# to more than one is a problem in local networks with hardhat's automining enabled, as it will brick
# the script. Therefore, we increase the required_confs for live networks only. No need to do it for testing
# nor localnets/devnets - that is with hardhat (including forks), with id 31337, and geth image, with id 10997.
def transaction_params():
    network.priority_fee("1 gwei")
    return 1 if chain.id in [hardhat, eth_localnet, arb_localnet] else 3
