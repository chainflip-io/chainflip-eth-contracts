from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy


@given(
    amount=strategy('uint', max_value=MIN_STAKE*2),
    staker=strategy('address'),
    # 30 days max should be far more than enough that the block height of the testing chain won't be above it
    expiryBlockDiff=strategy('uint', max_value=int(30*DAY/SECS_PER_BLOCK))
)
def test_registerClaim_amount_rand(cf, stakedMin, amount, staker, expiryBlockDiff):
    registerClaimTest(cf, cf.stakeManager.tx, MIN_STAKE, JUNK_INT, EMISSION_PER_BLOCK, MIN_STAKE, amount, cf.DENICE, web3.eth.blockNumber + expiryBlockDiff)


# Specific amounts that should/shouldn't work


def test_registerClaim_min_amount(cf, stakedMin):
    registerClaimTest(cf, cf.stakeManager.tx, MIN_STAKE, JUNK_INT, EMISSION_PER_BLOCK, MIN_STAKE, MIN_STAKE, cf.DENICE, web3.eth.blockNumber+(2*CLAIM_BLOCK_DELAY))


def test_registerClaim_max_amount(cf, stakedMin):
    stakeMinTx, initAmount = stakedMin
    # Want to calculate inflation 1 block into the future because that's when the tx will execute
    newLastMintBlockNum = web3.eth.blockNumber + 1
    maxValidAmount = initAmount + getInflation(cf.stakeManager.tx.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)

    registerClaimTest(cf, cf.stakeManager.tx, MIN_STAKE, JUNK_INT, EMISSION_PER_BLOCK, MIN_STAKE, maxValidAmount, cf.DENICE, web3.eth.blockNumber+(2*CLAIM_BLOCK_DELAY))


def test_registerClaim_min_expiryBlock(cf, stakedMin):
    registerClaimTest(cf, cf.stakeManager.tx, MIN_STAKE, JUNK_INT, EMISSION_PER_BLOCK, MIN_STAKE, MIN_STAKE, cf.DENICE, web3.eth.blockNumber+2+CLAIM_BLOCK_DELAY)


def test_registerClaim_rev_just_under_min_expiryBlock(cf, stakedMin):
    _, amount = stakedMin
    args = (JUNK_INT, amount, cf.DENICE, web3.eth.blockNumber + CLAIM_BLOCK_DELAY)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(NULL_SIG_DATA, *args)
    with reverts(REV_MSG_EXPIRY_TOO_SOON):
        cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)


def test_registerClaim_claim_expired(cf, stakedMin):
    _, amount = stakedMin
    args1 = (JUNK_INT, amount, cf.DENICE, web3.eth.blockNumber+2+CLAIM_BLOCK_DELAY)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(NULL_SIG_DATA, *args1)
    cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args1)
    
    chain.mine(CLAIM_BLOCK_DELAY+1)
    registerClaimTest(cf, cf.stakeManager.tx, MIN_STAKE, JUNK_INT, EMISSION_PER_BLOCK, MIN_STAKE, MIN_STAKE, cf.DENICE, web3.eth.blockNumber+3+CLAIM_BLOCK_DELAY)


def test_registerClaim_rev_claim_not_expired(cf, stakedMin):
    _, amount = stakedMin
    args1 = (JUNK_INT, amount, cf.DENICE, web3.eth.blockNumber+2+CLAIM_BLOCK_DELAY)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(NULL_SIG_DATA, *args1)
    cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args1)

    with reverts(REV_MSG_CLAIM_EXISTS):
        cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args1)


def test_registerClaim_rev_nodeID(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    args = (0, amount, receiver, web3.eth.blockNumber+2+CLAIM_BLOCK_DELAY)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(NULL_SIG_DATA, *args)
    with reverts(REV_MSG_NZ_UINT):
        cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)


def test_registerClaim_rev_staker(cf, stakedMin):
    _, amount = stakedMin
    args = (JUNK_INT, amount, ZERO_ADDR, web3.eth.blockNumber+2+CLAIM_BLOCK_DELAY)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(NULL_SIG_DATA, *args)
    with reverts(REV_MSG_NZ_ADDR):
        cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)


def test_registerClaim_rev_msgHash(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    args = (JUNK_INT, amount, cf.DENICE, web3.eth.blockNumber+2+CLAIM_BLOCK_DELAY)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(NULL_SIG_DATA, *args)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.stakeManager.registerClaim(sigData, *args)


def test_registerClaim_rev_sig(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    args = (JUNK_INT, amount, cf.DENICE, web3.eth.blockNumber+2+CLAIM_BLOCK_DELAY)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(NULL_SIG_DATA, *args)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1

    with reverts(REV_MSG_SIG):
        cf.stakeManager.registerClaim(sigData, *args)


# Can't use the normal StakeManager to test this since there's obviously
# intentionally no way to get FLIP out of the contract without calling `registerClaim`,
# so we have to use StakeManagerVulnerable which inherits StakeManager and
# has `testSendFLIP` in it to simulate some kind of hack
@given(amount=strategy('uint256', min_value=1, max_value=MIN_STAKE+1))
def test_stake_rev_noFish(cf, vulnerableR3ktStakeMan, amount):
    smVuln, _ = vulnerableR3ktStakeMan
    args = (JUNK_INT, 1, cf.DENICE, web3.eth.blockNumber+2+CLAIM_BLOCK_DELAY)

    callDataNoSig = smVuln.registerClaim.encode_input(NULL_SIG_DATA, *args)
    with reverts(REV_MSG_NO_FISH):
        smVuln.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)