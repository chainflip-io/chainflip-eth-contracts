from re import A
from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy
from shared_tests_tokenVesting import *

import pytest


@given(st_sleepTime=strategy("uint256", max_value=YEAR * 2))
def test_revoke(addrs, cf, tokenVestingNoStaking, maths, st_sleepTime):
    tv, cliff, end, total = tokenVestingNoStaking

    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0
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
    check_state_noStaking(
        cliff,
        tv,
        cf,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        True,
        end,
        True,
        True,
    )
    assert tv.released(cf.flip) == 0
    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0

    # Release leftover amount. Adding st_sleepTime to test that we are not following
    # the vesting curve once it's been revoked
    chain.sleep(st_sleepTime)
    if releasable > 0:
        tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})
        check_released(tv, cf, tx, addrs.BENEFICIARY, releasable, releasable)
    else:
        release_revert(tv, cf, addrs.BENEFICIARY)
    assert cf.flip.balanceOf(tv) == 0


def test_revoke_rev_revoker(a, addrs, cf, tokenVestingNoStaking):
    tv, _, _, _ = tokenVestingNoStaking

    for ad in a:
        if ad != addrs.REVOKER:
            with reverts(REV_MSG_NOT_REVOKER):
                tv.revoke(cf.flip, {"from": ad})


def test_revoke_rev_revokable(addrs, cf, TokenVestingNoStaking):
    start = getChainTime()
    cliff = start + QUARTER_YEAR
    end = start + QUARTER_YEAR + YEAR

    tv = addrs.DEPLOYER.deploy(
        TokenVestingNoStaking,
        addrs.BENEFICIARY,
        ZERO_ADDR,
        cliff,
        end,
        BENEF_NON_TRANSF,
    )

    with reverts(REV_MSG_NOT_REVOKER):
        tv.revoke(cf.flip, {"from": addrs.REVOKER})


def test_revoke_rev_revoked(addrs, cf, tokenVestingNoStaking):
    tv, _, _, _ = tokenVestingNoStaking

    tv.revoke(cf.flip, {"from": addrs.REVOKER})

    with reverts(REV_MSG_TOKEN_REVOKED):
        tv.revoke(cf.flip, {"from": addrs.REVOKER})
