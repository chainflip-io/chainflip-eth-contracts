from consts import *
from brownie import chain
from brownie.test import given, strategy
from shared_tests_tokenVesting import *


def test_release_rev_no_tokens(addrs, cf, tokenVestingStaking):
    tv, _, _ = tokenVestingStaking

    release_revert(tv, cf, addrs.BENEFICIARY)


@given(st_sleepTime=strategy("uint256", max_value=YEAR * 2))
def test_release(addrs, cf, tokenVestingStaking, addressHolder, st_sleepTime):
    tv, end, total = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0

    chain.sleep(st_sleepTime)

    if getChainTime() < end:
        release_revert(tv, cf, addrs.BENEFICIARY)
    else:
        tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})

        # Check release
        check_released(tv, cf, tx, addrs.BENEFICIARY, total, total)
        # Shouldn't've changed
        check_state_staking(
            cf.stateChainGateway,
            addressHolder,
            tv,
            addrs.BENEFICIARY,
            addrs.REVOKER,
            True,
            end,
            True,
            False,
        )


def test_release_all(addrs, cf, tokenVestingStaking, addressHolder):
    tv, end, total = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0

    chain.sleep(YEAR + QUARTER_YEAR)

    tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})

    # Check release
    check_released(tv, cf, tx, addrs.BENEFICIARY, total, total)
    # Shouldn't've changed
    check_state_staking(
        cf.stateChainGateway,
        addressHolder,
        tv,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        True,
        end,
        True,
        False,
    )


def test_consecutive_releases_after_cliff(
    addrs, cf, tokenVestingStaking, maths, addressHolder
):
    tv, end, total = tokenVestingStaking

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

    # In staking  conctrracts cliff == end
    # No amount can be released until we reach the cliff == end where it is all releasable
    for timestamp in timestamps:

        chain.sleep(timestamp - previousTimestamp)
        if getChainTime() < end:
            release_revert(tv, cf, addrs.BENEFICIARY)
        else:
            tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})

            totalReleased = (
                maths.simulateRelease(total, tx.timestamp, end, end)
                if tx.timestamp < end
                else total
            )
            newlyReleased = totalReleased - accomulatedReleases

            # Check release
            check_released(tv, cf, tx, addrs.BENEFICIARY, totalReleased, newlyReleased)

            # Shouldn't've changed
            check_state_staking(
                cf.stateChainGateway,
                addressHolder,
                tv,
                addrs.BENEFICIARY,
                addrs.REVOKER,
                True,
                end,
                True,
                False,
            )
            accomulatedReleases += newlyReleased

        previousTimestamp = timestamp

    assert cf.flip.balanceOf(addrs.BENEFICIARY) <= total

    release_revert(tv, cf, addrs.BENEFICIARY)


def test_release_staking_rewards_after_end(
    addrs, cf, tokenVestingStaking, maths, addressHolder
):
    tv, end, total = tokenVestingStaking

    test_release_all(addrs, cf, tokenVestingStaking, addressHolder)

    # Mimic rewards received from staking
    cf.flip.transfer(tv, total, {"from": addrs.DEPLOYER})

    tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})

    totalReleased = total + total

    check_released(tv, cf, tx, addrs.BENEFICIARY, totalReleased, total)

    # Shouldn't've changed
    check_state_staking(
        cf.stateChainGateway,
        addressHolder,
        tv,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        True,
        end,
        True,
        False,
    )


# Test that the assert(!canStake) is not reached => cliff == end == start + QUARTER_YEAR + YEAR
@given(st_sleepTime=strategy("uint256", min_value=QUARTER_YEAR, max_value=YEAR * 2))
def test_release_around_cliff(
    addrs, cf, tokenVestingStaking, addressHolder, st_sleepTime
):
    tv, end, total = tokenVestingStaking

    chain.sleep(st_sleepTime)

    if getChainTime() >= end:
        tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})
        # Check release
        check_released(tv, cf, tx, addrs.BENEFICIARY, total, total)
        # Shouldn't've changed
        check_state_staking(
            cf.stateChainGateway,
            addressHolder,
            tv,
            addrs.BENEFICIARY,
            addrs.REVOKER,
            True,
            end,
            True,
            False,
        )
    else:
        release_revert(tv, cf, addrs.BENEFICIARY)
