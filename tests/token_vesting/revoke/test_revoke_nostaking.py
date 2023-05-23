from re import A
from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy
from shared_tests_tokenVesting import *

import pytest


@given(st_sleepTime=strategy("uint256", max_value=YEAR * 2))
def test_revoke(
    addrs, cf, tokenVestingNoStaking, maths, st_sleepTime, scGatewayReference
):
    tv, cliff, end, total = tokenVestingNoStaking

    assert cf.flip.balanceOf(addrs.INVESTOR) == 0
    assert cf.flip.balanceOf(addrs.REVOKER) == 0
    revokedAmount = 0

    chain.sleep(st_sleepTime)

    if getChainTime() < cliff:
        tx = tv.revoke(cf.flip, {"from": addrs.REVOKER})
        releasable = 0
    elif getChainTime() >= end:
        with reverts(REV_MSG_VESTING_EXPIRED):
            tv.revoke(cf.flip, {"from": addrs.REVOKER})
        return
    else:
        tx = tv.revoke(cf.flip, {"from": addrs.REVOKER})

        releasable = (
            maths.simulateRelease(total, tx.timestamp, end, cliff)
            if tx.timestamp < end
            else total
        )

    revokedAmount = total - releasable

    check_revoked(tv, cf, tx, addrs.REVOKER, revokedAmount, total - revokedAmount)

    # Shouldn't've changed
    check_state(
        tv,
        cf,
        addrs.INVESTOR,
        addrs.REVOKER,
        True,
        cliff,
        end,
        False,
        True,
        cf.stateChainGateway,
        True,
        scGatewayReference,
    )
    assert tv.released(cf.flip) == 0
    assert cf.flip.balanceOf(addrs.INVESTOR) == 0

    # Release leftover amount. Adding st_sleepTime to test that we are not following
    # the vesting curve once it's been revoked
    chain.sleep(st_sleepTime)
    if releasable > 0:
        tx = tv.release(cf.flip, {"from": addrs.INVESTOR})
        check_released(tv, cf, tx, addrs.INVESTOR, releasable, releasable)
    else:
        release_revert(tv, cf, addrs.INVESTOR)
    assert cf.flip.balanceOf(tv) == 0


def test_revoke_rev_revoker(a, addrs, cf, tokenVestingNoStaking):
    tv, cliff, end, total = tokenVestingNoStaking

    for ad in a:
        if ad != addrs.REVOKER:
            with reverts(REV_MSG_NOT_REVOKER):
                tv.revoke(cf.flip, {"from": ad})


def test_revoke_rev_revokable(addrs, cf, TokenVesting):
    start = getChainTime()
    cliff = start + QUARTER_YEAR
    end = start + QUARTER_YEAR + YEAR

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        ZERO_ADDR,
        cliff,
        end,
        NON_STAKABLE,
        BENEF_NON_TRANSF,
        cf.stateChainGateway,
    )

    with reverts(REV_MSG_NOT_REVOKER):
        tv.revoke(cf.flip, {"from": addrs.REVOKER})


def test_revoke_rev_revoked(a, addrs, cf, tokenVestingNoStaking):
    tv, cliff, end, total = tokenVestingNoStaking

    tv.revoke(cf.flip, {"from": addrs.REVOKER})

    with reverts(REV_MSG_ALREADY_REVOKED):
        tv.revoke(cf.flip, {"from": addrs.REVOKER})

    with reverts(REV_MSG_CANNOT_RETRIEVE):
        tv.retrieveRevokedFunds(cf.flip, {"from": addrs.REVOKER})
