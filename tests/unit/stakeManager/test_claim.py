from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


@given(amount=strategy('uint256', max_value=MIN_STAKE*2))
def test_claim_amount_rand(cf, stakedMin, web3, amount):
    claimTest(cf, web3, cf.stakeManager.tx, MIN_STAKE, JUNK_INT, EMISSION_PER_BLOCK, MIN_STAKE, amount, cf.DENICE, 0)


def test_claim_min(cf, stakedMin, web3):
    claimTest(cf, web3, cf.stakeManager.tx, MIN_STAKE, JUNK_INT, EMISSION_PER_BLOCK, MIN_STAKE, MIN_STAKE, cf.DENICE, 0)


def test_claim_rev_amount_just_under_min(cf, stakedMin, web3):
    claimTest(cf, web3, cf.stakeManager.tx, MIN_STAKE, JUNK_INT, EMISSION_PER_BLOCK, MIN_STAKE, MIN_STAKE, cf.DENICE, 0)


def test_claim_max(cf, stakedMin, web3):
    stakeMinTx, initAmount = stakedMin
    # Want to calculate inflation 1 block into the future because that's when the tx will execute
    newLastMintBlockNum = web3.eth.blockNumber + 1
    maxValidAmount = initAmount + getInflation(cf.stakeManager.tx.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)

    claimTest(cf, web3, cf.stakeManager.tx, MIN_STAKE, JUNK_INT, EMISSION_PER_BLOCK, MIN_STAKE, maxValidAmount, cf.DENICE, 0)


def test_claim_rev_just_over_max(cf, stakedMin, web3):
    stakeMinTx, initAmount = stakedMin
    # Want to calculate inflation 1 block into the future because that's when the tx will execute
    newLastMintBlockNum = web3.eth.blockNumber + 1
    maxValidAmount = initAmount + getInflation(cf.stakeManager.tx.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)

    claimTest(cf, web3, cf.stakeManager.tx, MIN_STAKE, JUNK_INT, EMISSION_PER_BLOCK, MIN_STAKE, maxValidAmount+1, cf.DENICE, 0)


def test_claim_rev_nodeID(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE

    callDataNoSig = cf.stakeManager.claim.encode_input(NULL_SIG_DATA, 0, receiver, amount)
    with reverts(REV_MSG_NZ_UINT):
        cf.stakeManager.claim(AGG_SIGNER_1.getSigData(callDataNoSig), 0, receiver, amount)


def test_claim_rev_staker(cf, stakedMin):
    _, amount = stakedMin
    receiver = ZERO_ADDR

    callDataNoSig = cf.stakeManager.claim.encode_input(NULL_SIG_DATA, JUNK_INT, receiver, amount)
    with reverts(REV_MSG_NZ_ADDR):
        cf.stakeManager.claim(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_INT, receiver, amount)


def test_claim_rev_msgHash(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    callDataNoSig = cf.stakeManager.claim.encode_input(NULL_SIG_DATA, JUNK_INT, receiver, amount)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.stakeManager.claim(sigData, JUNK_INT, receiver, amount)


def test_claim_rev_sig(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    callDataNoSig = cf.stakeManager.claim.encode_input(NULL_SIG_DATA, JUNK_INT, receiver, amount)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1

    with reverts(REV_MSG_SIG):
        cf.stakeManager.claim(sigData, JUNK_INT, receiver, amount)


# Can't use the normal StakeManager to test this since there's obviously
# intentionally no way to get FLIP out of the contract without calling `claim`,
# so we have to use StakeManagerVulnerable which inherits StakeManager and
# has `testSendFLIP` in it to simulate some kind of hack
@given(amount=strategy('uint256', min_value=1, max_value=MIN_STAKE+1))
def test_stake_rev_noFish(cf, vulnerableR3ktStakeMan, FLIP, web3, amount):
    smVuln, _ = vulnerableR3ktStakeMan
    newLastMintBlockNum = web3.eth.blockNumber + 1
    maxValidAmount = MIN_STAKE + getInflation(smVuln.tx.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)
    # Ensure test doesn't fail because there aren't enough coins
    withdrawAmount = maxValidAmount - amount
    callDataNoSig = smVuln.claim.encode_input(NULL_SIG_DATA, JUNK_INT, cf.CHARLIE, withdrawAmount)
    with reverts(REV_MSG_NO_FISH):
        smVuln.claim(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_INT, cf.CHARLIE, withdrawAmount)
