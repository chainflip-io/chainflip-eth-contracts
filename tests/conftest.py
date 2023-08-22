import pytest
from consts import *
from deploy import *
from deploy import (
    deploy_Chainflip_contracts,
    deploy_new_multicall,
    deploy_new_cfReceiver,
)
from utils import *


# Test isolation
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Deploy the contracts for repeated tests without having to redeploy each time
@pytest.fixture(scope="module")
def cfDeploy(
    a, KeyManager, Vault, StateChainGateway, FLIP, DeployerContract, AddressChecker
):
    # Deploy with an unused EOA (a[9]) so deployer != safekeeper as in production
    return deploy_Chainflip_contracts(
        a[9],
        KeyManager,
        Vault,
        StateChainGateway,
        FLIP,
        DeployerContract,
        AddressChecker,
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

    cf.flip.transfer(cf.ALICE, MAX_TEST_FUND, {"from": cf.SAFEKEEPER})
    cf.flip.transfer(cf.BOB, MAX_TEST_FUND, {"from": cf.SAFEKEEPER})

    return cf


# Deploys SchnorrSECP256K1Test to enable testing of SchnorrSECP256K1
@pytest.fixture(scope="module")
def schnorrTest(cf, SchnorrSECP256K1Test):
    return cf.SAFEKEEPER.deploy(SchnorrSECP256K1Test)


@pytest.fixture(scope="module")
def multicall(cf, Multicall):
    return deploy_new_multicall(cf.SAFEKEEPER, Multicall, cf.vault.address)


# Stake the minimum amount
@pytest.fixture(scope="module")
def fundedMin(cf):
    amount = MIN_FUNDING
    cf.flip.approve(cf.stateChainGateway.address, amount, {"from": cf.ALICE})
    return (
        cf.stateChainGateway.fundStateChainAccount(
            JUNK_HEX, amount, {"from": cf.ALICE}
        ),
        amount,
    )


# Register a redemption to use executeRedemption with
@pytest.fixture(scope="module")
def redemptionRegistered(cf, fundedMin):
    _, amount = fundedMin
    expiryTime = getChainTime() + (2 * REDEMPTION_DELAY)
    args = (JUNK_HEX, amount, cf.DENICE, expiryTime, ZERO_ADDR)

    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.stateChainGateway.registerRedemption, nonces, *args
    )
    tx = cf.stateChainGateway.registerRedemption(
        sigData,
        *args,
        {"from": cf.ALICE},
    )

    return tx, (
        amount,
        cf.DENICE,
        tx.timestamp + REDEMPTION_DELAY,
        expiryTime,
        ZERO_ADDR,
    )


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
    addrs.BENEFICIARY = a[11]

    return addrs


@pytest.fixture(scope="module")
def maths(addrs, MockMaths):
    return addrs.DEPLOYER.deploy(MockMaths)


@pytest.fixture(scope="module")
def mockStProvider(cf, addrs, Minter, Burner, stFLIP):

    stFlip = addrs.DEPLOYER.deploy(stFLIP)

    burner = addrs.DEPLOYER.deploy(Burner, stFlip.address, cf.flip)

    # For the sake of testing setting the staking address (output) to be the Burner.
    # This way the real FLIP goes there automatically when staking.
    staking_address = burner

    minter = addrs.DEPLOYER.deploy(
        Minter, stFlip.address, cf.flip.address, staking_address
    )

    stFlip.initialize(minter.address, burner.address)

    return stFlip, minter, burner, staking_address


@pytest.fixture(scope="module")
def addressHolder(cf, addrs, AddressHolder, mockStProvider):
    stFLIP, minter, burner, _ = mockStProvider

    return deploy_addressHolder(
        addrs.DEPLOYER,
        AddressHolder,
        addrs.DEPLOYER,
        cf.stateChainGateway,
        minter.address,
        burner.address,
        stFLIP.address,
    )


@pytest.fixture(scope="module")
def tokenVestingNoStaking(addrs, cf, TokenVestingNoStaking):

    # This was hardcoded to a timestamp, but ganache uses real-time when we run
    # the tests, so we should use relative values instead of absolute ones
    start = getChainTime()
    cliff = start + QUARTER_YEAR
    end = start + QUARTER_YEAR + YEAR

    total = MAX_TEST_FUND

    tv = deploy_tokenVestingNoStaking(
        addrs.DEPLOYER,
        TokenVestingNoStaking,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        cliff,
        end,
        BENEF_TRANSF,
        cf.flip,
        total,
    )

    return tv, cliff, end, total


@pytest.fixture(scope="module")
def tokenVestingStaking(addrs, cf, TokenVestingStaking, addressHolder):
    # This was hardcoded to a timestamp, but ganache uses real-time when we run
    # the tests, so we should use relative values instead of absolute ones
    start = getChainTime()
    end = start + QUARTER_YEAR + YEAR

    total = MAX_TEST_FUND

    tv = deploy_tokenVestingStaking(
        addrs.DEPLOYER,
        TokenVestingStaking,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        end,
        BENEF_TRANSF,
        addressHolder,
        cf.flip,
        total,
    )
    return tv, end, total


# Deploy CFReceiver Mock contracts for testing purposes
@pytest.fixture(scope="module")
def cfTester(cf, CFTester):
    return deploy_new_cfReceiver(cf.SAFEKEEPER, CFTester, cf.vault)


@pytest.fixture(scope="module")
def cfTester(cf, CFTester):
    return deploy_new_cfReceiver(cf.SAFEKEEPER, CFTester, cf.vault)


@pytest.fixture(scope="module")
def cfReceiverFailMock(cf, CFReceiverFailMock):
    return deploy_new_cfReceiver(cf.SAFEKEEPER, CFReceiverFailMock, cf.vault)


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
def mockUSDT(cf, MockUSDT):
    return cf.SAFEKEEPER.deploy(MockUSDT, "Tether USD", "USDT", INIT_USDC_SUPPLY)


@pytest.fixture(scope="module")
def mockKeyManagers(
    cf,
    KeyManagerMock0,
    KeyManagerMock1,
    KeyManagerMock2,
    KeyManagerMock3,
    KeyManagerMock4,
    KeyManagerMock5,
):
    km_0 = cf.SAFEKEEPER.deploy(KeyManagerMock0)
    km_1 = cf.SAFEKEEPER.deploy(KeyManagerMock1)
    km_2 = cf.SAFEKEEPER.deploy(KeyManagerMock2, cf.BOB)
    km_3 = cf.SAFEKEEPER.deploy(KeyManagerMock3, cf.BOB)
    km_4 = cf.SAFEKEEPER.deploy(KeyManagerMock4, cf.BOB, cf.DENICE)
    km_5 = cf.SAFEKEEPER.deploy(KeyManagerMock5, cf.BOB, cf.DENICE)

    kmMocks_arbitrary_addresses = [km_0, km_1, km_2, km_3, km_4, km_5]

    km_0 = cf.SAFEKEEPER.deploy(KeyManagerMock0)
    km_1 = cf.SAFEKEEPER.deploy(KeyManagerMock1)
    km_2 = cf.SAFEKEEPER.deploy(KeyManagerMock2, cf.keyManager.getGovernanceKey())
    km_3 = cf.SAFEKEEPER.deploy(KeyManagerMock3, cf.keyManager.getGovernanceKey())
    km_4 = cf.SAFEKEEPER.deploy(
        KeyManagerMock4,
        cf.keyManager.getGovernanceKey(),
        cf.keyManager.getCommunityKey(),
    )
    km_5 = cf.SAFEKEEPER.deploy(
        KeyManagerMock5,
        cf.keyManager.getGovernanceKey(),
        cf.keyManager.getCommunityKey(),
    )

    kmMocks_valid_addresses = [km_0, km_1, km_2, km_3, km_4, km_5]

    return kmMocks_arbitrary_addresses, kmMocks_valid_addresses
