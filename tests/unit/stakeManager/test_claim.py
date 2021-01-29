from consts import *
from brownie import reverts
from brownie.test import given, strategy
import time


# Hypothesis/brownie doesn't allow you to specifically include values when generating random
# inputs through @given, so this is a common fcn that can be used for `test_claim` and
# similar tests that test specific desired values
def claimTest(a, cf, stakedMin, web3, amount):
    stakeMinTx, initAmount = stakedMin
    receiver = cf.DENICE
    # Want to calculate inflation 1 block into the future because that's when the tx will execute
    newLastMintBlockNum = web3.eth.blockNumber + 1
    inflation = getInflation(cf.stakeManager.tx.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)
    maxValidAmount = initAmount + inflation

    assert cf.flip.balanceOf(receiver) == 0

    callDataNoSig = cf.stakeManager.claim.encode_input(NULL_SIG_DATA, JUNK_INT, receiver, amount)

    if amount == 0:
        with reverts(REV_MSG_NZ_UINT):
            cf.stakeManager.claim(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_INT, receiver, amount)
    elif amount <= maxValidAmount:
        tx = cf.stakeManager.claim(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_INT, receiver, amount)
        
        # Check things that should've changed
        assert cf.flip.balanceOf(receiver) == amount
        assert newLastMintBlockNum == tx.block_number
        assert cf.flip.balanceOf(cf.stakeManager) == maxValidAmount - amount
        assert cf.stakeManager.getTotalStakeInFuture(0) == maxValidAmount - amount
        assert tx.events["Claimed"][0].values() == [JUNK_INT, amount]
        assert tx.events["Transfer"][0].values() == [ZERO_ADDR, cf.stakeManager.address, inflation]
        # Check things that shouldn't have changed
        assert cf.stakeManager.getEmissionPerBlock() == EMISSION_PER_BLOCK
        assert cf.stakeManager.getMinimumStake() == MIN_STAKE
    else:
        with reverts(REV_MSG_EXCEED_BAL):
            cf.stakeManager.claim(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_INT, receiver, amount)
    

@given(amount=strategy('uint256', max_value=MIN_STAKE*2))
def test_claim(a, cf, stakedMin, web3, amount):
    claimTest(a, cf, stakedMin, web3, amount)


def test_claim_min(a, cf, stakedMin, web3):
    claimTest(a, cf, stakedMin, web3, MIN_STAKE)


def test_claim_rev_amount_just_under_min(a, cf, stakedMin, web3):
    claimTest(a, cf, stakedMin, web3, MIN_STAKE-1)


def test_claim_max(a, cf, stakedMin, web3):
    stakeMinTx, initAmount = stakedMin
    # Want to calculate inflation 1 block into the future because that's when the tx will execute
    newLastMintBlockNum = web3.eth.blockNumber + 1
    maxValidAmount = initAmount + getInflation(cf.stakeManager.tx.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)

    claimTest(a, cf, stakedMin, web3, maxValidAmount)


def test_claim_rev_just_over_max(a, cf, stakedMin, web3):
    stakeMinTx, initAmount = stakedMin
    # Want to calculate inflation 1 block into the future because that's when the tx will execute
    newLastMintBlockNum = web3.eth.blockNumber + 1
    maxValidAmount = initAmount + getInflation(cf.stakeManager.tx.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)

    claimTest(a, cf, stakedMin, web3, maxValidAmount+1)


def test_claim_rev_staker(cf, stakedMin):
    _, amount = stakedMin
    receiver = ZERO_ADDR

    callDataNoSig = cf.stakeManager.claim.encode_input(NULL_SIG_DATA, JUNK_INT, receiver, amount)
    with reverts(REV_MSG_NZ_ADDR):
        cf.stakeManager.claim(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_INT, receiver, amount)


def test_claim_rev_nodeID(a, cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE

    callDataNoSig = cf.stakeManager.claim.encode_input(NULL_SIG_DATA, 0, receiver, amount)
    with reverts(REV_MSG_NZ_UINT):
        cf.stakeManager.claim(AGG_SIGNER_1.getSigData(callDataNoSig), 0, receiver, amount)


def test_claim_rev_msgHash(a, cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    callDataNoSig = cf.stakeManager.claim.encode_input(NULL_SIG_DATA, JUNK_INT, receiver, amount)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.stakeManager.claim(sigData, JUNK_INT, receiver, amount)


def test_claim_rev_sig(a, cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    callDataNoSig = cf.stakeManager.claim.encode_input(NULL_SIG_DATA, JUNK_INT, receiver, amount)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1

    with reverts(REV_MSG_SIG):
        cf.stakeManager.claim(sigData, JUNK_INT, receiver, amount)
