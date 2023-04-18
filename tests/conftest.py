import pytest
from consts import *
from deploy import deploy_Chainflip_contracts
from deploy import deploy_Chainflip_contracts
from brownie import chain
from brownie.network import priority_fee
from utils import *


# Test isolation
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Deploy the contracts for repeated tests without having to redeploy each time
@pytest.fixture(scope="module")
def cfDeploy(a, KeyManager, Vault, StakeManager, FLIP, DeployerContract):
    # Deploy with an unused EOA (a[9]) so deployer != safekeeper as in production
    return deploy_Chainflip_contracts(
        a[9], KeyManager, Vault, StakeManager, FLIP, DeployerContract
    )


# Deploy the contracts and set up common test environment
@pytest.fixture(scope="module")
def cf(a, cfDeploy):
    cf = cfDeploy

    # It's a bit easier to not get mixed up with accounts if they're named
    # Can't define this in consts because `a` needs to be imported into the test
    cf.SAFEKEEPER = cfDeploy.safekeeper
    cf.ALICE = a[1]
    cf.BOB = a[2]
    cf.CHARLIE = a[3]
    cf.DENICE = a[4]

    # It's the same as SAFEKEEPER but shouldn't cause confusion tbh
    cf.GOVERNOR = cfDeploy.gov
    # Set a second governor for tests
    cf.GOVERNOR_2 = a[5]

    # Set Community Key addresses for tests - a[6] & a[7]
    cf.COMMUNITY_KEY = cfDeploy.communityKey
    cf.COMMUNITY_KEY_2 = a[7]

    cf.flip.transfer(cf.ALICE, MAX_TEST_STAKE, {"from": cf.SAFEKEEPER})
    cf.flip.transfer(cf.BOB, MAX_TEST_STAKE, {"from": cf.SAFEKEEPER})

    return cf


# Deploys SchnorrSECP256K1Test to enable testing of SchnorrSECP256K1
@pytest.fixture(scope="module")
def schnorrTest(cf, SchnorrSECP256K1Test):
    return cf.SAFEKEEPER.deploy(SchnorrSECP256K1Test)


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

    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.stakeManager.registerClaim, nonces, *args
    )
    tx = cf.stakeManager.registerClaim(
        sigData,
        *args,
        {"from": cf.ALICE},
    )

    return tx, (amount, cf.DENICE, tx.timestamp + CLAIM_DELAY, expiryTime)


# Deploy a generic token
@pytest.fixture(scope="module")
def token(cf, Token):
    return cf.SAFEKEEPER.deploy(Token, "NotAPonzi", "NAP", INIT_TOKEN_SUPPLY)


# Deploy a generic token
@pytest.fixture(scope="module")
def token2(cf, Token):
    return cf.SAFEKEEPER.deploy(Token, "NotAPonzi2", "NAP2", INIT_TOKEN_SUPPLY)


# Vesting
@pytest.fixture(scope="module")
def addrs(a):
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
        cliff,
        end,
        NON_STAKABLE,
        cf.stakeManager,
    )

    total = MAX_TEST_STAKE

    cf.flip.transfer(tv, total, {"from": addrs.DEPLOYER})

    return tv, cliff, end, total


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
        cliff,
        end,
        STAKABLE,
        cf.stakeManager,
    )

    total = MAX_TEST_STAKE

    cf.flip.transfer(tv, total, {"from": addrs.DEPLOYER})

    return tv, cliff, end, total


# Deploy CFReceiver Mock contracts for testing purposes


@pytest.fixture(scope="module")
def cfReceiverMock(cf, CFReceiverMock):
    return cf.SAFEKEEPER.deploy(CFReceiverMock, cf.vault)


@pytest.fixture(scope="module")
def cfReceiverFailMock(cf, CFReceiverFailMock):
    return cf.SAFEKEEPER.deploy(CFReceiverFailMock, cf.vault)


@pytest.fixture(scope="module")
def cfReceiverTryMock(cf, cfReceiverFailMock, CFReceiverTryMock):
    return cf.SAFEKEEPER.deploy(CFReceiverTryMock, cf.vault, cfReceiverFailMock)


@pytest.fixture(scope="module")
def cfDexAggMock(cf, DexAggSrcChainMock, DEXMock, DexAggDstChainMock):
    srcChain = 1
    dexMock = cf.SAFEKEEPER.deploy(DEXMock)
    dexAggSrcChainMock = cf.SAFEKEEPER.deploy(DexAggSrcChainMock, cf.vault)
    dexAggDstChainMock = cf.SAFEKEEPER.deploy(
        DexAggDstChainMock, cf.vault, srcChain, toHex(dexAggSrcChainMock.address)
    )
    return (dexMock, dexAggSrcChainMock, dexAggDstChainMock, srcChain)


@pytest.fixture(scope="module")
def cfLoopbackMock(cf, LoopBackMock):
    return cf.SAFEKEEPER.deploy(LoopBackMock, cf.vault)


@pytest.fixture(scope="module")
def mockUsdc(cf, MockUSDC):
    return cf.SAFEKEEPER.deploy(MockUSDC, "USD Coin", "USDC", INIT_USDC_SUPPLY)


@pytest.fixture(scope="module")
def utils(cf, Utils):
    return cf.SAFEKEEPER.deploy(Utils)


@pytest.fixture(scope="module")
def multicall(cf, SquidMulticall):
    return cf.SAFEKEEPER.deploy(SquidMulticall)
