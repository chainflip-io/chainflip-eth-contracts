from consts import *
from brownie import chain
from brownie.test import given, strategy
from shared_tests_tokenVesting import *


def test_release_rev_no_tokens(addrs, cf, tokenVestingStaking):
    tv, _, _, _ = tokenVestingStaking

    release_revert(tv, cf, addrs.BENEFICIARY)


@given(st_sleepTime=strategy("uint256", max_value=YEAR * 2))
def test_release(addrs, cf, tokenVestingStaking, addressHolder, st_sleepTime, maths):
    tv, stakingVestingEnd, end, total = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0

    chain.sleep(st_sleepTime)

    if getChainTime() < stakingVestingEnd:
        release_revert(tv, cf, addrs.BENEFICIARY)
    else:
        tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})

        newlyReleased = (
            maths.simulateReleaseSt(total, tx.timestamp, end, stakingVestingEnd)
            if tx.timestamp < end
            else total
        )

        # Check release
        assert tx.events["TokensReleased"][0].values() == (cf.flip, newlyReleased)

        # Shouldn't've changed
        check_state_staking(
            cf.stateChainGateway,
            addressHolder,
            tv,
            stakingVestingEnd,
            addrs.BENEFICIARY,
            addrs.REVOKER,
            True,
            end,
            True,
            False,
        )


def test_release_all(addrs, cf, tokenVestingStaking, addressHolder):
    tv, stakingVestingEnd, end, total = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0

    chain.sleep(end + QUARTER_YEAR)

    tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})

    # Check release
    assert tx.events["TokensReleased"][0].values() == (cf.flip, total)

    # Shouldn't've changed
    check_state_staking(
        cf.stateChainGateway,
        addressHolder,
        tv,
        stakingVestingEnd,
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
    tv, stakingVestingEnd, end, total = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0

    accomulatedReleases = 0

    # Substracting current time because they are on absolute terms
    timestamps = [
        stakingVestingEnd - 100,
        stakingVestingEnd + QUARTER_YEAR,
        stakingVestingEnd + QUARTER_YEAR * 2,
        end - 100,
        end + 100,
    ]

    # In staking  conctrracts cliff == end
    # No amount can be released until we reach the cliff == end where it is all releasable
    for timestamp in timestamps:

        chain.sleep(timestamp - getChainTime())
        if getChainTime() < stakingVestingEnd:
            release_revert(tv, cf, addrs.BENEFICIARY)
        else:
            tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})

            totalReleased = (
                maths.simulateReleaseSt(total, tx.timestamp, end, stakingVestingEnd)
                if tx.timestamp < end
                else total
            )
            newlyReleased = totalReleased - accomulatedReleases

            # Check release
            assert tx.events["TokensReleased"][0].values() == (cf.flip, newlyReleased)

            # Shouldn't've changed
            check_state_staking(
                cf.stateChainGateway,
                addressHolder,
                tv,
                stakingVestingEnd,
                addrs.BENEFICIARY,
                addrs.REVOKER,
                True,
                end,
                True,
                False,
            )
            accomulatedReleases += newlyReleased

    assert cf.flip.balanceOf(addrs.BENEFICIARY) <= total

    release_revert(tv, cf, addrs.BENEFICIARY)


def test_release_staking_rewards_after_end(
    addrs, cf, tokenVestingStaking, addressHolder
):
    tv, stakingVestingEnd, end, total = tokenVestingStaking

    test_release_all(addrs, cf, tokenVestingStaking, addressHolder)

    # Mimic rewards received from staking
    cf.flip.transfer(tv, total, {"from": addrs.DEPLOYER})

    tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})

    assert tx.events["TokensReleased"][0].values() == (cf.flip, total)

    # Shouldn't've changed
    check_state_staking(
        cf.stateChainGateway,
        addressHolder,
        tv,
        stakingVestingEnd,
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
    tv, stakingVestingEnd, end, total = tokenVestingStaking

    chain.sleep(st_sleepTime)

    if getChainTime() >= stakingVestingEnd:
        tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})
        # Check release
        assert tx.events["TokensReleased"]["token"] == cf.flip
        assert (
            tx.events["TokensReleased"]["amount"] > 0 if tx.timestamp < end else total
        )
        # Shouldn't've changed
        check_state_staking(
            cf.stateChainGateway,
            addressHolder,
            tv,
            stakingVestingEnd,
            addrs.BENEFICIARY,
            addrs.REVOKER,
            True,
            end,
            True,
            False,
        )
    else:
        release_revert(tv, cf, addrs.BENEFICIARY)
