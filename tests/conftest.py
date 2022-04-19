import pytest
from consts import *
from deploy import deploy_initial_Chainflip_contracts
from deploy import deploy_set_Chainflip_contracts
from brownie import chain
from brownie.network import priority_fee
from utils import *


# Test isolation
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Deploy the contracts for repeated tests without having to redeploy each time
@pytest.fixture(scope="module")
def cfDeploy(a, KeyManager, Vault, StakeManager, FLIP):
    return deploy_set_Chainflip_contracts(
        a[0], a[6], KeyManager, Vault, StakeManager, FLIP
    )


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

    # It's the same as DEPLOYER (a[0]) but shouldn't cause confusion tbh
    cf.GOVERNOR = cfDeploy.gov
    # Set a second governor for tests
    cf.GOVERNOR_2 = a[5]

    # Set Community Key addresses for tests - a[6] & a[7]
    cf.COMMUNITY_KEY = cfDeploy.communityKey
    cf.COMMUNITY_KEY_2 = a[7]

    cf.flip.transfer(cf.ALICE, MAX_TEST_STAKE, {"from": cf.DEPLOYER})
    cf.flip.transfer(cf.BOB, MAX_TEST_STAKE, {"from": cf.DEPLOYER})

    return cf


# Deploy the contracts for repeated tests without having to redeploy each time, with
# all addresses whitelisted
@pytest.fixture(scope="module")
def cfDeployAllWhitelist(a, KeyManager, Vault, StakeManager, FLIP):
    cf = deploy_initial_Chainflip_contracts(
        a[0], a[6], KeyManager, Vault, StakeManager, FLIP
    )
    cf.whitelisted = [cf.vault, cf.stakeManager, cf.keyManager, cf.flip] + list(a)
    cf.keyManager.setCanConsumeKeyNonce(cf.whitelisted)

    return cf


# Deploy the contracts and set up common test environment, with all addresses whitelisted
@pytest.fixture(scope="module")
def cfAW(a, cfDeployAllWhitelist):
    cf = cfDeployAllWhitelist

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

    # It's the same as DEPLOYER (a[0]) but shouldn't cause confusion tbh
    cf.GOVERNOR = cfDeployAllWhitelist.gov
    # Set a second governor for tests
    cf.GOVERNOR_2 = a[5]

    # Set Community Key addresses for tests - a[6] & a[7]
    cf.COMMUNITY_KEY = cfDeployAllWhitelist.communityKey
    cf.COMMUNITY_KEY_2 = a[7]

    cf.flip.transfer(cf.ALICE, MAX_TEST_STAKE, {"from": cf.DEPLOYER})
    cf.flip.transfer(cf.BOB, MAX_TEST_STAKE, {"from": cf.DEPLOYER})

    return cf


# Deploys SchnorrSECP256K1Test to enable testing of SchnorrSECP256K1
@pytest.fixture(scope="module")
def schnorrTest(cf, SchnorrSECP256K1Test):
    return cf.DEPLOYER.deploy(SchnorrSECP256K1Test)


# Stake the minimum amount
@pytest.fixture(scope="module")
def stakedMin(cf):
    amount = MIN_STAKE
    cf.flip.approve(cf.stakeManager.address, amount, {"from": cf.ALICE})
    return (
        cf.stakeManager.stake(JUNK_HEX, amount, NON_ZERO_ADDR, {"from": cf.ALICE}),
        amount,
    )


# Register a claim to use executeClaim with
@pytest.fixture(scope="module")
def claimRegistered(cf, stakedMin):
    _, amount = stakedMin
    expiryTime = getChainTime() + (2 * CLAIM_DELAY)
    args = (JUNK_HEX, amount, cf.DENICE, expiryTime)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    tx = cf.stakeManager.registerClaim(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), *args
    )

    return tx, (amount, cf.DENICE, tx.timestamp + CLAIM_DELAY, expiryTime)


# Deploy a generic token
@pytest.fixture(scope="module")
def token(cf, Token):
    return cf.DEPLOYER.deploy(Token, "NotAPonzi", "NAP", INIT_TOKEN_SUPPLY)


# Deploy a generic token
@pytest.fixture(scope="module")
def token2(cf, Token):
    return cf.DEPLOYER.deploy(Token, "NotAPonzi2", "NAP2", INIT_TOKEN_SUPPLY)


# Vesting
@pytest.fixture(scope="module")
def addrs(a, TokenVesting):
    class Context:
        pass

    addrs = Context()
    addrs.DEPLOYER = a[0]
    addrs.REVOKER = a[10]
    addrs.INVESTOR = a[11]

    return addrs


@pytest.fixture(scope="module")
def maths(addrs, MockMaths):
    return addrs.DEPLOYER.deploy(MockMaths)


@pytest.fixture(scope="module")
def tokenVestingNoStaking(addrs, cf, TokenVesting):

    # This was hardcoded to a timestamp, but ganache uses real-time when we run
    # the tests, so we should use relative values instead of absolute ones
    start = getChainTime()
    cliff = start + QUARTER_YEAR
    end = start + QUARTER_YEAR + YEAR

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        REVOCABLE,
        start,
        cliff,
        end,
        NON_STAKABLE,
        cf.stakeManager,
    )

    total = MAX_TEST_STAKE

    cf.flip.transfer(tv, total, {"from": addrs.DEPLOYER})

    return tv, start, cliff, end, total


@pytest.fixture(scope="module")
def tokenVestingStaking(addrs, cf, TokenVesting):

    # This was hardcoded to a timestamp, but ganache uses real-time when we run
    # the tests, so we should use relative values instead of absolute ones
    start = getChainTime()
    end = start + QUARTER_YEAR + YEAR
    cliff = end

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        REVOCABLE,
        start,
        cliff,
        end,
        STAKABLE,
        cf.stakeManager,
    )

    total = MAX_TEST_STAKE

    cf.flip.transfer(tv, total, {"from": addrs.DEPLOYER})

    return tv, start, cliff, end, total
