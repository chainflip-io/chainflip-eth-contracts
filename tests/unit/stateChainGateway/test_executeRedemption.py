from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy


@given(
    st_nodeID=strategy("uint", exclude=0),
    st_sender=strategy("address"),
)
def test_executeRedemption_empty(cf, st_nodeID, st_sender):
    assert cf.stateChainGateway.getPendingRedemption(st_nodeID) == NULL_CLAIM

    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeRedemption(st_nodeID, {"from": st_sender})


# Need to also register a redemption in this since the st_amounts sent etc depend on registerRedemption
@given(
    st_nodeID=strategy("uint", exclude=0),
    st_amount=strategy("uint", max_value=MIN_FUNDING * 2, exclude=0),
    st_redeem_address=strategy("address"),
    st_expiryTimeDiff=strategy(
        "uint", min_value=REDEMPTION_DELAY, max_value=2 * REDEMPTION_DELAY
    ),
    st_sleepTime=strategy("uint", min_value=5, max_value=3 * REDEMPTION_DELAY),
)
def test_executeRedemption_rand(
    cf, st_nodeID, st_amount, st_redeem_address, st_expiryTimeDiff, st_sleepTime
):
    # Differences in the time.time() and chain time cause errors between runs when there's no actual issue
    if not (REDEMPTION_DELAY - 100 < st_expiryTimeDiff < REDEMPTION_DELAY + 100):
        st_nodeID = web3.toHex(st_nodeID)
        assert cf.stateChainGateway.getPendingRedemption(st_nodeID) == NULL_CLAIM
        scgStartBal = cf.flip.balanceOf(cf.stateChainGateway)
        st_redeemAddress = cf.flip.balanceOf(st_redeem_address)

        expiryTime = getChainTime() + st_expiryTimeDiff + 5
        args = (st_nodeID, st_amount, st_redeem_address, expiryTime, ZERO_ADDR)

        tx = signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args)

        assert cf.stateChainGateway.getPendingRedemption(st_nodeID) == (
            st_amount,
            st_redeem_address,
            tx.timestamp + REDEMPTION_DELAY,
            expiryTime,
            ZERO_ADDR,
        )
        assert cf.flip.balanceOf(cf.stateChainGateway) == scgStartBal

        maxValidst_amount = cf.flip.balanceOf(cf.stateChainGateway)

        chain.sleep(st_sleepTime)

        if getChainTime() < (tx.timestamp + REDEMPTION_DELAY - 1):
            with reverts(REV_MSG_NOT_ON_TIME):
                cf.stateChainGateway.executeRedemption(st_nodeID, {"from": cf.ALICE})
        elif getChainTime() > expiryTime:
            tx = cf.stateChainGateway.executeRedemption(st_nodeID, {"from": cf.ALICE})
            assert tx.events["RedemptionExpired"][0].values() == [st_nodeID, st_amount]

        elif st_amount > maxValidst_amount:
            with reverts(REV_MSG_INTEGER_OVERFLOW):
                cf.stateChainGateway.executeRedemption(st_nodeID, {"from": cf.ALICE})
        else:
            tx = cf.stateChainGateway.executeRedemption(st_nodeID, {"from": cf.ALICE})

            # Check things that should've changed
            assert cf.stateChainGateway.getPendingRedemption(st_nodeID) == NULL_CLAIM
            assert (
                cf.flip.balanceOf(cf.stateChainGateway) == maxValidst_amount - st_amount
            )
            assert tx.events["RedemptionExecuted"][0].values() == [st_nodeID, st_amount]
            assert cf.flip.balanceOf(st_redeem_address) == st_redeemAddress + st_amount
            assert tx.return_value == (st_redeem_address, st_amount)

            # Check things that shouldn't have changed
            assert cf.stateChainGateway.getMinimumFunding() == MIN_FUNDING


def test_executeRedemption_min_delay(cf, redemptionRegistered):
    _, redemption = redemptionRegistered
    assert cf.stateChainGateway.getPendingRedemption(JUNK_HEX) == redemption

    maxValidst_amount = cf.flip.balanceOf(cf.stateChainGateway)

    assert maxValidst_amount != 0

    chain.sleep(REDEMPTION_DELAY)
    tx = cf.stateChainGateway.executeRedemption(JUNK_HEX, {"from": cf.ALICE})

    # Check things that should've changed
    assert cf.stateChainGateway.getPendingRedemption(JUNK_HEX) == NULL_CLAIM
    assert cf.flip.balanceOf(cf.stateChainGateway) == maxValidst_amount - redemption[0]
    assert tx.events["RedemptionExecuted"][0].values() == [JUNK_HEX, redemption[0]]
    assert cf.flip.balanceOf(redemption[1]) == redemption[0]
    assert tx.return_value == (redemption[1], redemption[0])

    # Check things that shouldn't have changed
    assert cf.stateChainGateway.getMinimumFunding() == MIN_FUNDING


def test_executeRedemption_max_delay(cf, redemptionRegistered):
    _, redemption = redemptionRegistered
    assert cf.stateChainGateway.getPendingRedemption(JUNK_HEX) == redemption

    maxValidst_amount = cf.flip.balanceOf(cf.stateChainGateway)

    chain.sleep(redemption[3] - getChainTime() - 2)
    tx = cf.stateChainGateway.executeRedemption(JUNK_HEX, {"from": cf.ALICE})

    # Check things that should've changed
    assert cf.stateChainGateway.getPendingRedemption(JUNK_HEX) == NULL_CLAIM
    assert cf.flip.balanceOf(cf.stateChainGateway) == maxValidst_amount - redemption[0]
    assert tx.events["RedemptionExecuted"][0].values() == [JUNK_HEX, redemption[0]]
    assert cf.flip.balanceOf(redemption[1]) == redemption[0]
    assert tx.return_value == (redemption[1], redemption[0])

    # Check things that shouldn't have changed
    assert cf.stateChainGateway.getMinimumFunding() == MIN_FUNDING


def test_executeRedemption_rev_too_early(cf):
    chain.sleep(REDEMPTION_DELAY - 5)

    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeRedemption(JUNK_HEX, {"from": cf.ALICE})


def test_executeRedemption_rev_too_late(cf, redemptionRegistered):
    _, redemption = redemptionRegistered
    chain.sleep(redemption[3] - getChainTime() + 5)

    tx = cf.stateChainGateway.executeRedemption(JUNK_HEX, {"from": cf.ALICE})
    assert tx.events["RedemptionExpired"][0].values() == [JUNK_HEX, redemption[0]]
    assert cf.stateChainGateway.getPendingRedemption(JUNK_HEX) == NULL_CLAIM
    assert tx.return_value == (redemption[1], 0)


def test_executeRedemption_rev_suspended(cf, redemptionRegistered):
    _, redemption = redemptionRegistered
    assert cf.stateChainGateway.getPendingRedemption(JUNK_HEX) == redemption

    chain.sleep(REDEMPTION_DELAY)

    # Suspend the StateChainGateway via governance
    cf.stateChainGateway.suspend({"from": cf.GOVERNOR})

    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.stateChainGateway.executeRedemption(JUNK_HEX, {"from": cf.ALICE})


# Need to also register a redemption in this since the st_amounts sent etc depend on registerRedemption
@given(
    st_redeem_address=strategy("address"),
    st_executor=strategy("address"),
    st_executor_address=strategy("address"),
)
def test_executeRedemption_rev_executor(
    cf, st_redeem_address, st_executor, st_executor_address
):
    # Different nodeID than the default registered Redemption
    nodeId = web3.toHex(JUNK_INT + 1)

    expiry_time = getChainTime() + (2 * REDEMPTION_DELAY)
    args = (nodeId, JUNK_INT, st_redeem_address, expiry_time, st_executor_address)

    tx = signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args)

    assert cf.stateChainGateway.getPendingRedemption(nodeId) == (
        JUNK_INT,
        st_redeem_address,
        tx.timestamp + REDEMPTION_DELAY,
        expiry_time,
        st_executor_address,
    )

    chain.sleep(REDEMPTION_DELAY)

    if st_executor == st_executor_address:
        tx = cf.stateChainGateway.executeRedemption(nodeId, {"from": st_executor})
        assert cf.stateChainGateway.getPendingRedemption(nodeId) == NULL_CLAIM
        assert tx.events["RedemptionExecuted"][0].values() == [nodeId, JUNK_INT]
        assert tx.return_value == (st_redeem_address, JUNK_INT)
    else:
        with reverts(REV_MSG_NOT_EXECUTOR):
            cf.stateChainGateway.executeRedemption(nodeId, {"from": st_executor})
