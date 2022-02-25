from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy
from shared_tests_tokenVesting import *


def test_release_rev_no_tokens(addrs, cf, tokenVestingStaking):
    tv, start, cliff, end, total = tokenVestingStaking

    release_revert (tv, cf, addrs.INVESTOR)

@given(sleepTime=strategy('uint256', max_value=YEAR*2))
def test_release(addrs, cf, tokenVestingStaking, maths, sleepTime):
    tv, start, cliff, end, total = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.INVESTOR) == 0

    chain.sleep(sleepTime)

    assert tv.cliff() == tv.end()

    if chain.time() < end:
            release_revert (tv, cf, addrs.INVESTOR)
    else:
        tx = tv.release(cf.flip, {'from': addrs.INVESTOR})

        # Check release
        check_released (tv, cf, tx, addrs.INVESTOR, total, total)
        # Shouldn't've changed
        check_state(tv, cf, addrs.INVESTOR, addrs.REVOKER, True, cliff, end, True, cf.stakeManager, 0)


def test_release_all(addrs, cf, tokenVestingStaking, maths):
    tv, start, cliff, end, total = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.INVESTOR) == 0

    chain.sleep(YEAR + QUARTER_YEAR)

    tx = tv.release(cf.flip, {'from': addrs.INVESTOR})

    # Check release
    check_released (tv, cf, tx, addrs.INVESTOR, total, total)
    # Shouldn't've changed
    check_state(tv, cf, addrs.INVESTOR, addrs.REVOKER, True, cliff, end, True, cf.stakeManager, 0)


def test_consecutive_releases_after_cliff(addrs, cf, tokenVestingStaking, maths):
    tv, start, cliff, end, total = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.INVESTOR) == 0

    accomulatedReleases = 0
    previousTimestamp = 0

    # Substracting 'start' because they are on absolute terms
    timestamps = [QUARTER_YEAR, QUARTER_YEAR*2, end-100-start, end-start+100 ]
    
    # In staking  conctrracts cliff == end
    # No amount can be released until we reach the cliff == end where it is all releasable
    for timestamp in timestamps:

        chain.sleep(timestamp-previousTimestamp)
        if chain.time() < end:
                release_revert (tv, cf, addrs.INVESTOR)
        else:
            tx = tv.release(cf.flip, {'from': addrs.INVESTOR})

            totalReleased = maths.simulateRelease(total, tx.timestamp, start, end, cliff)  if tx.timestamp < end else total
            newlyReleased = totalReleased - accomulatedReleases

            # Check release
            check_released (tv, cf, tx, addrs.INVESTOR, totalReleased, newlyReleased)

            # Shouldn't've changed
            check_state(tv, cf, addrs.INVESTOR, addrs.REVOKER, True, cliff, end, True, cf.stakeManager, 0)
            accomulatedReleases += newlyReleased

        previousTimestamp = timestamp

    assert cf.flip.balanceOf(addrs.INVESTOR) <= total

    release_revert (tv, cf, addrs.INVESTOR)

def test_release_staking_rewards_after_end(addrs, cf, tokenVestingStaking, maths):
    tv, start, cliff, end, total = tokenVestingStaking

    test_release_all(addrs, cf, tokenVestingStaking, maths)

    # Mimic rewards recieved from staking
    cf.flip.transfer(tv, total, {'from': addrs.DEPLOYER})

    tx = tv.release(cf.flip, {'from': addrs.INVESTOR})

    totalReleased = total + total

    check_released (tv, cf, tx, addrs.INVESTOR, totalReleased, total)

    # Shouldn't've changed
    check_state(tv, cf, addrs.INVESTOR, addrs.REVOKER, True, cliff, end, True, cf.stakeManager, 0)


# Test that the assert(!canStake) is not reached => cliff == end == start + QUARTER_YEAR + YEAR
@given(sleepTime=strategy('uint256', min_value = QUARTER_YEAR ,max_value= YEAR*2))
def test_release_around_cliff (addrs, cf, tokenVestingStaking, maths,sleepTime):
    tv, start, cliff, end, total = tokenVestingStaking

    chain.sleep(sleepTime)

    if (chain.time() >= cliff & cliff==end):
        tx = tv.release(cf.flip, {'from': addrs.INVESTOR})
        # Check release
        check_released (tv, cf, tx, addrs.INVESTOR, total, total)
        # Shouldn't've changed
        check_state(tv, cf, addrs.INVESTOR, addrs.REVOKER, True, cliff, end, True, cf.stakeManager, 0)
    else:
        release_revert (tv, cf, addrs.INVESTOR)

