from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy
from shared_tests_tokenVesting import *


def test_release_rev_no_tokens(addrs, cf, tokenVestingNoStaking):
    tv, cliff, end, total = tokenVestingNoStaking

    release_revert(tv, cf, addrs.INVESTOR)


@given(st_sleepTime=strategy("uint256", max_value=YEAR * 2))
def test_release(
    addrs, cf, tokenVestingNoStaking, maths, st_sleepTime, scGatewayReference
):
    tv, cliff, end, total = tokenVestingNoStaking

    assert cf.flip.balanceOf(addrs.INVESTOR) == 0

    chain.sleep(st_sleepTime)

    if getChainTime() < cliff:
        release_revert(tv, cf, addrs.INVESTOR)
    else:
        tx = tv.release(cf.flip, {"from": addrs.INVESTOR})

        newlyReleased = (
            maths.simulateRelease(total, tx.timestamp, end, cliff)
            if tx.timestamp < end
            else total
        )
        # Check release
        check_released(tv, cf, tx, addrs.INVESTOR, newlyReleased, newlyReleased)
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
            0,
            scGatewayReference,
        )


def test_release_all(addrs, cf, tokenVestingNoStaking, scGatewayReference):
    tv, cliff, end, total = tokenVestingNoStaking

    assert cf.flip.balanceOf(addrs.INVESTOR) == 0

    chain.sleep(YEAR + QUARTER_YEAR)

    tx = tv.release(cf.flip, {"from": addrs.INVESTOR})

    # Check release
    check_released(tv, cf, tx, addrs.INVESTOR, total, total)
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
        0,
        scGatewayReference,
    )


def test_consecutive_releases_after_cliff(
    addrs, cf, tokenVestingNoStaking, maths, scGatewayReference
):
    tv, cliff, end, total = tokenVestingNoStaking

    assert cf.flip.balanceOf(addrs.INVESTOR) == 0

    accomulatedReleases = 0
    previousTimestamp = 0

    # Substracting current time because they are on absolute terms
    timestamps = [
        QUARTER_YEAR,
        QUARTER_YEAR * 2,
        end - 100 - getChainTime(),
        end - getChainTime(),
    ]

    for timestamp in timestamps:

        chain.sleep(timestamp - previousTimestamp)
        print(timestamp)
        tx = tv.release(cf.flip, {"from": addrs.INVESTOR})

        totalReleased = (
            maths.simulateRelease(total, tx.timestamp, end, cliff)
            if tx.timestamp < end
            else total
        )
        newlyReleased = totalReleased - accomulatedReleases

        # Check release
        check_released(tv, cf, tx, addrs.INVESTOR, totalReleased, newlyReleased)

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
            0,
            scGatewayReference,
        )

        previousTimestamp = timestamp
        accomulatedReleases += newlyReleased

    assert cf.flip.balanceOf(addrs.INVESTOR) <= total

    release_revert(tv, cf, addrs.INVESTOR)
