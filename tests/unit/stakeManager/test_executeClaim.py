from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy

# Need to also register a claim in this since the st_amounts sent etc depend on registerClaim
@given(
    st_nodeID=strategy("uint", exclude=0),
    st_amount=strategy("uint", max_value=MIN_STAKE * 2, exclude=0),
    st_staker=strategy("address"),
    st_expiryTimeDiff=strategy(
        "uint", min_value=CLAIM_DELAY, max_value=2 * CLAIM_DELAY
    ),
    st_sleepTime=strategy("uint", min_value=5, max_value=3 * CLAIM_DELAY),
)
def test_executeClaim_rand(
    cf, st_nodeID, st_amount, st_staker, st_expiryTimeDiff, st_sleepTime
):
    # Differences in the time.time() and chain time cause errors between runs when there's no actual issue
    if not (CLAIM_DELAY - 100 < st_expiryTimeDiff < CLAIM_DELAY + 100):
        st_nodeID = web3.toHex(st_nodeID)
        assert cf.stakeManager.getPendingClaim(st_nodeID) == NULL_CLAIM
        smStartBal = cf.flip.balanceOf(cf.stakeManager)
        st_stakerStartBal = cf.flip.balanceOf(st_staker)

        expiryTime = getChainTime() + st_expiryTimeDiff + 5
        args = (st_nodeID, st_amount, st_staker, expiryTime)

        tx = signed_call_cf(cf, cf.stakeManager.registerClaim, *args)

        assert cf.stakeManager.getPendingClaim(st_nodeID) == (
            st_amount,
            st_staker,
            tx.timestamp + CLAIM_DELAY,
            expiryTime,
        )
        assert cf.flip.balanceOf(cf.stakeManager) == smStartBal

        maxValidst_amount = cf.flip.balanceOf(cf.stakeManager)

        chain.sleep(st_sleepTime)

        if getChainTime() < (tx.timestamp + CLAIM_DELAY - 1):
            with reverts(REV_MSG_NOT_ON_TIME):
                cf.stakeManager.executeClaim(st_nodeID, {"from": cf.ALICE})
        elif getChainTime() > expiryTime:
            tx = cf.stakeManager.executeClaim(st_nodeID, {"from": cf.ALICE})
            assert tx.events["ClaimExpired"][0].values() == [st_nodeID, st_amount]

        elif st_amount > maxValidst_amount:
            with reverts(REV_MSG_INTEGER_OVERFLOW):
                cf.stakeManager.executeClaim(st_nodeID, {"from": cf.ALICE})
        else:
            tx = cf.stakeManager.executeClaim(st_nodeID, {"from": cf.ALICE})

            # Check things that should've changed
            assert cf.stakeManager.getPendingClaim(st_nodeID) == NULL_CLAIM
            assert cf.flip.balanceOf(cf.stakeManager) == maxValidst_amount - st_amount
            assert tx.events["ClaimExecuted"][0].values() == [st_nodeID, st_amount]
            assert cf.flip.balanceOf(st_staker) == st_stakerStartBal + st_amount
            # Check things that shouldn't have changed
            assert cf.stakeManager.getMinimumStake() == MIN_STAKE


def test_executeClaim_min_delay(cf, claimRegistered):
    _, claim = claimRegistered
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == claim

    maxValidst_amount = cf.flip.balanceOf(cf.stakeManager)

    assert maxValidst_amount != 0

    chain.sleep(CLAIM_DELAY)
    tx = cf.stakeManager.executeClaim(JUNK_HEX, {"from": cf.ALICE})

    # Check things that should've changed
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == NULL_CLAIM
    assert cf.flip.balanceOf(cf.stakeManager) == maxValidst_amount - claim[0]
    assert tx.events["ClaimExecuted"][0].values() == [JUNK_HEX, claim[0]]
    assert cf.flip.balanceOf(claim[1]) == claim[0]

    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE


def test_executeClaim_max_delay(cf, claimRegistered):
    _, claim = claimRegistered
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == claim

    maxValidst_amount = cf.flip.balanceOf(cf.stakeManager)

    chain.sleep(claim[3] - getChainTime() - 2)
    tx = cf.stakeManager.executeClaim(JUNK_HEX, {"from": cf.ALICE})

    # Check things that should've changed
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == NULL_CLAIM
    assert cf.flip.balanceOf(cf.stakeManager) == maxValidst_amount - claim[0]
    assert tx.events["ClaimExecuted"][0].values() == [JUNK_HEX, claim[0]]
    assert cf.flip.balanceOf(claim[1]) == claim[0]

    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE


def test_executeClaim_rev_too_early(cf, claimRegistered):
    _, claim = claimRegistered
    chain.sleep(CLAIM_DELAY - 5)

    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stakeManager.executeClaim(JUNK_HEX, {"from": cf.ALICE})


def test_executeClaim_rev_too_late(cf, claimRegistered):
    _, claim = claimRegistered
    chain.sleep(claim[3] - getChainTime() + 5)

    tx = cf.stakeManager.executeClaim(JUNK_HEX, {"from": cf.ALICE})
    assert tx.events["ClaimExpired"][0].values() == [JUNK_HEX, claim[0]]
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == NULL_CLAIM


def test_executeClaim_rev_suspended(cf, claimRegistered):
    _, claim = claimRegistered
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == claim

    chain.sleep(CLAIM_DELAY)

    # Suspend the stakemananger via governance
    cf.stakeManager.suspend({"from": cf.GOVERNOR})

    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.stakeManager.executeClaim(JUNK_HEX, {"from": cf.ALICE})
