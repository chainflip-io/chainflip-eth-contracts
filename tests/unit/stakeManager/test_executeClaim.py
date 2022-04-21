from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy


# Need to also register a claim in this since the amounts sent etc depend on registerClaim
@given(
    nodeID=strategy("uint", exclude=0),
    amount=strategy("uint", max_value=MIN_STAKE * 2, exclude=0),
    staker=strategy("address"),
    expiryTimeDiff=strategy("uint", min_value=CLAIM_DELAY, max_value=2 * CLAIM_DELAY),
    sleepTime=strategy("uint", min_value=5, max_value=3 * CLAIM_DELAY),
)
def test_executeClaim_rand(
    cf, stakedMin, nodeID, amount, staker, expiryTimeDiff, sleepTime
):
    # Differences in the time.time() and chain time cause errors between runs when there's no actual issue
    if not (CLAIM_DELAY - 100 < expiryTimeDiff < CLAIM_DELAY + 100):
        nodeID = web3.toHex(nodeID)
        assert cf.stakeManager.getPendingClaim(nodeID) == NULL_CLAIM
        smStartBal = cf.flip.balanceOf(cf.stakeManager)
        stakerStartBal = cf.flip.balanceOf(staker)

        expiryTime = getChainTime() + expiryTimeDiff + 5
        args = (nodeID, amount, staker, expiryTime)
        callDataNoSig = cf.stakeManager.registerClaim.encode_input(
            agg_null_sig(cf.keyManager.address, chain.id), *args
        )
        tx1 = cf.stakeManager.registerClaim(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), *args
        )

        assert cf.stakeManager.getPendingClaim(nodeID) == (
            amount,
            staker,
            tx1.timestamp + CLAIM_DELAY,
            expiryTime,
        )
        assert cf.flip.balanceOf(cf.stakeManager) == smStartBal

        maxValidAmount = cf.flip.balanceOf(cf.stakeManager)

        chain.sleep(sleepTime)

        if (
            getChainTime() < tx1.timestamp + CLAIM_DELAY - 1
            or getChainTime() > expiryTime
        ):
            with reverts(REV_MSG_NOT_ON_TIME):
                cf.stakeManager.executeClaim(nodeID)
        elif amount > maxValidAmount:
            with reverts(REV_MSG_INTEGER_OVERFLOW):
                cf.stakeManager.executeClaim(nodeID)
        else:
            tx = cf.stakeManager.executeClaim(nodeID)

            # Check things that should've changed
            assert cf.stakeManager.getPendingClaim(nodeID) == NULL_CLAIM
            assert cf.flip.balanceOf(cf.stakeManager) == maxValidAmount - amount
            assert tx.events["ClaimExecuted"][0].values() == [nodeID, amount]
            assert cf.flip.balanceOf(staker) == stakerStartBal + amount
            # Check things that shouldn't have changed
            assert cf.stakeManager.getMinimumStake() == MIN_STAKE


def test_executeClaim_min_delay(cf, claimRegistered):
    _, claim = claimRegistered
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == claim

    maxValidAmount = cf.flip.balanceOf(cf.stakeManager)

    assert maxValidAmount != 0

    chain.sleep(CLAIM_DELAY)
    tx = cf.stakeManager.executeClaim(JUNK_HEX)

    # Check things that should've changed
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == NULL_CLAIM
    assert cf.flip.balanceOf(cf.stakeManager) == maxValidAmount - claim[0]
    assert tx.events["ClaimExecuted"][0].values() == [JUNK_HEX, claim[0]]
    assert cf.flip.balanceOf(claim[1]) == claim[0]

    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE


def test_executeClaim_max_delay(cf, claimRegistered):
    _, claim = claimRegistered
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == claim

    maxValidAmount = cf.flip.balanceOf(cf.stakeManager)

    chain.sleep(claim[3] - getChainTime() - 2)
    tx = cf.stakeManager.executeClaim(JUNK_HEX)

    # Check things that should've changed
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == NULL_CLAIM
    assert cf.flip.balanceOf(cf.stakeManager) == maxValidAmount - claim[0]
    assert tx.events["ClaimExecuted"][0].values() == [JUNK_HEX, claim[0]]
    assert cf.flip.balanceOf(claim[1]) == claim[0]

    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE


def test_executeClaim_rev_too_early(cf, claimRegistered):
    _, claim = claimRegistered
    chain.sleep(CLAIM_DELAY - 5)

    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stakeManager.executeClaim(JUNK_HEX)


def test_executeClaim_rev_too_late(cf, claimRegistered):
    _, claim = claimRegistered
    chain.sleep(claim[3] - getChainTime() + 5)

    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stakeManager.executeClaim(JUNK_HEX)


def test_executeClaim_rev_suspended(cf, claimRegistered):
    _, claim = claimRegistered
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == claim

    chain.sleep(CLAIM_DELAY)

    # Suspend the stakemananger via governance
    cf.stakeManager.suspend({"from": cf.GOVERNOR})

    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.stakeManager.executeClaim(JUNK_HEX)
