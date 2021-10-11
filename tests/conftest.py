import pytest
from consts import *
from deploy import deploy_initial_Chainflip_contracts
from brownie import chain
from brownie.network import priority_fee


# Test isolation
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Deploy the contracts for repeated tests without having to redeploy each time
@pytest.fixture(scope="module")
def cfDeploy(a, KeyManager, Vault, StakeManager, FLIP):
    return deploy_initial_Chainflip_contracts(a[0], KeyManager, Vault, StakeManager, FLIP)


# Deploy the contracts and set up common test environment
@pytest.fixture(scope="module")
def cf(a, cfDeploy):
    cf = cfDeploy

    # It's a bit easier to not get mixed up with accounts if they're named
    # Can't define this in consts because `a` needs to be imported into the test
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

    cf.flip.transfer(cf.ALICE, MAX_TEST_STAKE, {'from': cf.DEPLOYER})
    cf.flip.transfer(cf.BOB, MAX_TEST_STAKE, {'from': cf.DEPLOYER})

    return cf


# Deploys SchnorrSECP256K1Test to enable testing of SchnorrSECP256K1
@pytest.fixture(scope="module")
def schnorrTest(cf, SchnorrSECP256K1Test):
    return cf.DEPLOYER.deploy(SchnorrSECP256K1Test)


# Stake the minimum amount
@pytest.fixture(scope="module")
def stakedMin(cf):
    amount = MIN_STAKE
    return cf.stakeManager.stake(JUNK_HEX, amount, NON_ZERO_ADDR, {'from': cf.ALICE}), amount


# Register a claim to use executeClaim with
@pytest.fixture(scope="module")
def claimRegistered(cf, stakedMin):
    _, amount = stakedMin
    expiryTime = chain.time() + CLAIM_DELAY + 5
    args = (JUNK_HEX, amount, cf.DENICE, expiryTime)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), *args)
    tx = cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)

    return tx, (amount, cf.DENICE, tx.timestamp + CLAIM_DELAY, expiryTime)


# Deploy a generic token
@pytest.fixture(scope="module")
def token(cf, Token):
    return cf.DEPLOYER.deploy(Token, "NotAPonzi", "NAP", INIT_TOKEN_SUPPLY)


# Deploy a generic token
@pytest.fixture(scope="module")
def token2(cf, Token):
    return cf.DEPLOYER.deploy(Token, "NotAPonzi2", "NAP2", INIT_TOKEN_SUPPLY)


# Deploy and initialise StakeManagerVulnerable, a vulnerable version of
# StakeManager so that we can test that the StakeManager behaves properly
# (with noFish) if FLIP was to be somehow siphoned out of the contract.
# This also puts the minimum stake in it.
@pytest.fixture(scope="module")
def vulnerableStakedStakeMan(cf, StakeManagerVulnerable, FLIP):
    smVuln = cf.DEPLOYER.deploy(StakeManagerVulnerable, cf.keyManager, MIN_STAKE, INIT_SUPPLY, NUM_GENESIS_VALIDATORS, GENESIS_STAKE)
    flipVuln = FLIP.at(smVuln.getFLIPAddress())
    # Can't set _FLIP in the constructor because it's made in the constructor
    # of StakeManager and getFLIPAddress is external
    smVuln.testSetFLIP(flipVuln)
    flipVuln.transfer(cf.ALICE, MAX_TEST_STAKE, {'from': cf.DEPLOYER})

    assert flipVuln.balanceOf(cf.CHARLIE) == 0
    # Need to stake 1st so that there's coins to hack out of it
    smVuln.stake(JUNK_HEX, MIN_STAKE, NON_ZERO_ADDR, {'from': cf.ALICE})

    return smVuln, flipVuln

# Siphon some FLIP out of a StakeManagerVulnerable so that it
# can be tested on post-siphon
@pytest.fixture(scope="module")
def vulnerableR3ktStakeMan(cf, vulnerableStakedStakeMan):
    smVuln, flipVuln = vulnerableStakedStakeMan
    amount = 1
    # Somebody r3ks us somehow
    smVuln.testSendFLIP(cf.CHARLIE, amount)
    assert flipVuln.balanceOf(cf.CHARLIE) == amount

    return vulnerableStakedStakeMan