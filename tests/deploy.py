from os import environ
from consts import *
from web3.auto import w3
from brownie import network


def deploy_initial_Chainflip_contracts(deployer, KeyManager, Vault, StakeManager, FLIP, *args):

    # Set the priority fee for all transactions
    network.priority_fee("1 gwei")

    class Context:
        pass

    cf = Context()

    environment = {}
    if args: environment = args[0]

    aggKey = environment.get('AGG_KEY')
    if aggKey:
        parity = aggKey[0:2]
        x = aggKey[2:]
        parity = "00" if parity == "02" or parity == "00" else "01"
        aggKey = [int(x, 16), int(parity, 16)]
    else: aggKey = AGG_SIGNER_1.getPubData()

    # TODO: Update this, GOV_KEY should now be a standard Ethereum address
    govKey = environment.get('GOV_KEY')
    if govKey:
        parity = govKey[0:2]
        x = govKey[2:]
        parity = "00" if parity == "02" or parity == "00" else "01"
        govKey = [int(x, 16), int(parity, 16)]
    else: govKey = GOV_SIGNER_1.getPubData()

    # `deployer` here is the governor
    cf.gov = deployer
    cf.keyManager = deployer.deploy(KeyManager, aggKey, cf.gov)

    numGenesisValidators = int(environment.get('NUM_GENESIS_VALIDATORS') or NUM_GENESIS_VALIDATORS)

    genesisStake = int(environment.get("GENESIS_STAKE") or GENESIS_STAKE)

    print(f'Deploying with AGG_KEY: {aggKey} and GOV_KEY: {govKey}')

    cf.vault = deployer.deploy(Vault, cf.keyManager)
    cf.stakeManager = deployer.deploy(StakeManager, cf.keyManager, MIN_STAKE, INIT_SUPPLY, numGenesisValidators, genesisStake)
    cf.flip = FLIP.at(cf.stakeManager.getFLIP())

    # Now fund the contracts that we expect the Validators to interact with so
    # that we can test the refund functionality
    prefund_contracts = environment.get('PREFUND_CONTRACTS')

    if prefund_contracts == "true" or prefund_contracts == "True" or prefund_contracts == None:
        print("Prefunding the contracts with 1 ETH each.")
        deployer.transfer(to=cf.keyManager, amount=ONE_ETH)
        deployer.transfer(to=cf.vault, amount=ONE_ETH)
        deployer.transfer(to=cf.stakeManager, amount=ONE_ETH)
    else:
        print("Contracts have not been prefunded.")

    return cf


# This should be used over deploy_initial_Chainflip_contracts for actual deployments
def deploy_set_Chainflip_contracts(deployer, KeyManager, Vault, StakeManager, FLIP, *args):
    cf = deploy_initial_Chainflip_contracts(deployer, KeyManager, Vault, StakeManager, FLIP, *args)
    cf.keyManager.setCanValidateSig([cf.vault, cf.stakeManager, cf.keyManager])

    return cf
