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
    cf.FR_DEPLOYER = {"from": cf.DEPLOYER}
    cf.ALICE = a[1]
    cf.FR_ALICE = {"from": cf.ALICE}
    cf.BOB = a[2]
    cf.FR_BOB = {"from": cf.BOB}
    cf.CHARLIE = a[3]
    cf.FR_CHARLIE = {"from": cf.CHARLIE}
    cf.DENICE = a[4]
    cf.FR_DENICE = {"from": cf.DENICE}
    
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
def schnorrTest(cf, SchnorrSECP256K1Test):
    return cf.DEPLOYER.deploy(SchnorrSECP256K1Test)


@pytest.fixture(scope="module")
def stakedMin(cf):
    amount = MIN_STAKE
    return cf.stakeManager.stake(JUNK_INT, amount, {'from': cf.ALICE}), amount


@pytest.fixture(scope="module")
def token(cf, Token):
    return cf.DEPLOYER.deploy(Token, "ShitCoin", "SC", 10**21)


@pytest.fixture(scope="module")
def vulnerableStakedStakeMan(cf, StakeManagerVulnerable, FLIP):
    smVuln = cf.DEPLOYER.deploy(StakeManagerVulnerable, cf.keyManager, EMISSION_PER_BLOCK, MIN_STAKE, INITIAL_SUPPLY)
    flipVuln = FLIP.at(smVuln.getFLIPAddress())
    # Can't set _FLIP in the constructor because it's made in the constructor
    # of StakeManager and getFLIPAddress is external
    smVuln.testSetFLIP(flipVuln)
    flipVuln.transfer(cf.ALICE, MAX_TEST_STAKE, {'from': cf.DEPLOYER})
    flipVuln.approve(smVuln, MAX_TEST_STAKE, {'from': cf.ALICE})
    
    assert flipVuln.balanceOf(cf.CHARLIE) == 0
    # Need to stake 1st so that there's coins to hack out of it
    smVuln.stake(JUNK_INT, MIN_STAKE, {'from': cf.ALICE})

    return smVuln, flipVuln

@pytest.fixture(scope="module")
def vulnerableR3ktStakeMan(cf, vulnerableStakedStakeMan):
    smVuln, flipVuln = vulnerableStakedStakeMan
    amount = 1
    # Somebody r3ks us somehow
    smVuln.testSendFLIP(cf.CHARLIE, amount)
    assert flipVuln.balanceOf(cf.CHARLIE) == amount

    return vulnerableStakedStakeMan