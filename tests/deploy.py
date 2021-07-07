from consts import *


def deploy_initial_ChainFlip_contracts(deployer, KeyManager, Vault, StakeManager, FLIP):
    class Context:
        pass

    cf = Context()
    cf.keyManager = deployer.deploy(KeyManager, AGG_SIGNER_1.getPubData(), GOV_SIGNER_1.getPubData())
    cf.vault = deployer.deploy(Vault, cf.keyManager)
    cf.stakeManager = deployer.deploy(StakeManager, cf.keyManager, EMISSION_PER_BLOCK, MIN_STAKE, INIT_SUPPLY)
    cf.flip = FLIP.at(cf.stakeManager.getFLIPAddress())

    return cf