from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
from utils import *


@given(amount=strategy('uint256', max_value=MAX_TEST_STAKE))
def test_stake_amount_rand(cf, amount):
    print(cf.flip.balanceOf(cf.stakeManager))
    if amount < MIN_STAKE:
        with reverts(REV_MSG_MIN_STAKE):
            cf.stakeManager.stake(JUNK_INT, amount, {'from': cf.ALICE})
    else:
        tx = cf.stakeManager.stake(JUNK_INT, amount, {'from': cf.ALICE})
        stakeTest(
            cf,
            0,
            JUNK_INT,
            cf.stakeManager.tx.block_number,
            EMISSION_PER_BLOCK,
            MIN_STAKE,
            tx,
            amount
        )


# For some reason the snapshot doesn't revert after this test,
# can't put it before `test_stake_amount_rand`
def test_stake_min(cf, stakedMin):
    stakeTest(
        cf,
        0,
        JUNK_INT,
        cf.stakeManager.tx.block_number,
        EMISSION_PER_BLOCK,
        MIN_STAKE,
        *stakedMin
    )


def test_stake_rev_amount_just_under_minStake(cf):
    with reverts(REV_MSG_MIN_STAKE):
        cf.stakeManager.stake(JUNK_INT, MIN_STAKE-1, {'from': cf.ALICE})


def test_stake_rev_nodeID_nz(cf):
    with reverts(REV_MSG_NZ_UINT):
        cf.stakeManager.stake(0, cf.stakeManager.getMinimumStake(), {'from': cf.ALICE})


# Can't use the normal StakeManager to test this since there's obviously
# intentionally no way to get FLIP out of the contract without calling `claim`,
# so we have to use StakeManagerVulnerable which inherits StakeManager and
# has `testSendFLIP` in it to simulate some kind of hack
@given(amount=strategy('uint256', min_value=1, max_value=MIN_STAKE))
def test_stake_rev_noFish(cf, vulnerableR3ktStakeMan, FLIP, amount):
    smVuln, _ = vulnerableR3ktStakeMan

    with reverts(REV_MSG_NO_FISH):
        smVuln.stake(JUNK_INT, MIN_STAKE, {'from': cf.ALICE})