import pytest
from consts import *



# Test isolation
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Deploy the contracts for repeated tests without having to redeploy each time

def deploy_initial_ChainFlip_contracts(a, KeyManager, Vault, StakeManager, FLIP):
    class Context:
        pass

    cf = Context()

    # It's a bit easier to not get mixed up with accounts if they're named
    # Can't define this in consts because a needs to be imported into the test
    cf.DEPLOYER = a[0]
    cf.ALICE = a[1]
    cf.BOB = a[2]
    cf.CHARLIE = a[3]
    cf.DENICE = a[4]
    
    cf.keyManager = cf.DEPLOYER.deploy(KeyManager, AGG_SIGNER_1.getPubData(), GOV_SIGNER_1.getPubData())
    cf.vault = cf.DEPLOYER.deploy(Vault, cf.keyManager)
    cf.stakeManager = cf.DEPLOYER.deploy(StakeManager, cf.keyManager, EMISSION_PER_BLOCK, MIN_STAKE, INITIAL_SUPPLY)
    cf.flip = FLIP.at(cf.stakeManager.getFLIPAddress())
    cf.flip.transfer(cf.ALICE, MAX_TEST_STAKE, {'from': cf.DEPLOYER})
    cf.flip.approve(cf.stakeManager, MAX_TEST_STAKE, {'from': cf.ALICE})
    cf.flip.transfer(cf.BOB, MAX_TEST_STAKE, {'from': cf.DEPLOYER})
    cf.flip.approve(cf.stakeManager, MAX_TEST_STAKE, {'from': cf.BOB})


    return cf


@pytest.fixture(scope="module")
def cf(a, KeyManager, Vault, StakeManager, FLIP):
    return deploy_initial_ChainFlip_contracts(a, KeyManager, Vault, StakeManager, FLIP)


@pytest.fixture(scope="module")
def stakedMin(a, cf):
    amount = cf.stakeManager.getMinimumStake()
    return cf.stakeManager.stake(JUNK_INT, amount, {'from': cf.ALICE}), amount


@pytest.fixture(scope="module")
def token(a, cf, Token):
    return cf.DEPLOYER.deploy(Token, "ShitCoin", "SC", 10**21)
