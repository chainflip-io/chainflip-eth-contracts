from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy
from shared_tests_tokenVesting import *


def test_release_rev_no_tokens(addrs, cf, tokenVestingNoStaking):
    tv, _, _, _ = tokenVestingNoStaking

    release_revert(tv, cf, addrs.BENEFICIARY)


@given(st_sleepTime=strategy("uint256", max_value=YEAR * 2))
def test_release(addrs, cf, tokenVestingNoStaking, maths, st_sleepTime):
    tv, cliff, end, total = tokenVestingNoStaking

    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0

    chain.sleep(st_sleepTime)

    if getChainTime() < cliff:
        release_revert(tv, cf, addrs.BENEFICIARY)
    else:
        tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})

        newlyReleased = (
            maths.simulateRelease(total, tx.timestamp, end, cliff)
            if tx.timestamp < end
            else total
        )
        # Check release
        check_released_noStaking(
            tv, cf, tx, addrs.BENEFICIARY, newlyReleased, newlyReleased
        )
        # Shouldn't've changed
        check_state_noStaking(
            cliff,
            tv,
            addrs.BENEFICIARY,
            addrs.REVOKER,
            True,
            end,
            True,
            False,
        )


def test_release_all(addrs, cf, tokenVestingNoStaking):
    tv, cliff, end, total = tokenVestingNoStaking

    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0

    chain.sleep(YEAR + QUARTER_YEAR)

    tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})

    # Check release
    check_released_noStaking(tv, cf, tx, addrs.BENEFICIARY, total, total)
    # Shouldn't've changed
    check_state_noStaking(
        cliff,
        tv,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        True,
        end,
        True,
        False,
    )


def test_consecutive_releases_after_cliff(addrs, cf, tokenVestingNoStaking, maths):
    tv, cliff, end, total = tokenVestingNoStaking

    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0

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
        tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})

        totalReleased = (
            maths.simulateRelease(total, tx.timestamp, end, cliff)
            if tx.timestamp < end
            else total
        )
        newlyReleased = totalReleased - accomulatedReleases

        # Check release
        check_released_noStaking(
            tv, cf, tx, addrs.BENEFICIARY, newlyReleased, totalReleased
        )

        # Shouldn't've changed
        check_state_noStaking(
            cliff,
            tv,
            addrs.BENEFICIARY,
            addrs.REVOKER,
            True,
            end,
            True,
            False,
        )

        previousTimestamp = timestamp
        accomulatedReleases += newlyReleased

    assert cf.flip.balanceOf(addrs.BENEFICIARY) <= total

    release_revert(tv, cf, addrs.BENEFICIARY)


def check_released_noStaking(tv, cf, tx, address, recentlyReleased, totalReleased):
    assert tx.events["TokensReleased"][0].values()[0] == cf.flip
    assert tx.events["TokensReleased"][0].values()[1] == recentlyReleased
    assert tv.released(cf.flip) == totalReleased
    assert cf.flip.balanceOf(address) == totalReleased
