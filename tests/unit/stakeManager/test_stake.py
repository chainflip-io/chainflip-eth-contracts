from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
from utils import *


@given(amount=strategy("uint256", max_value=MAX_TEST_STAKE))
def test_stake_amount_rand(cf, amount):
    if amount < MIN_STAKE:
        with reverts(REV_MSG_MIN_STAKE):
            cf.flip.approve(cf.stakeManager.address, amount, {"from": cf.ALICE})
            cf.stakeManager.stake(JUNK_HEX, amount, NON_ZERO_ADDR, {"from": cf.ALICE})
    else:
        cf.flip.approve(cf.stakeManager.address, amount, {"from": cf.ALICE})
        tx = cf.stakeManager.stake(JUNK_HEX, amount, NON_ZERO_ADDR, {"from": cf.ALICE})
        stakeTest(cf, 0, JUNK_HEX, MIN_STAKE, tx, amount, NON_ZERO_ADDR)


# For some reason the snapshot doesn't revert after this test,
# can't put it before `test_stake_amount_rand`
def test_stake_min(cf, stakedMin):
    stakeTest(cf, 0, JUNK_HEX, MIN_STAKE, *stakedMin, NON_ZERO_ADDR)


def test_stake_rev_amount_just_under_minStake(cf):
    with reverts(REV_MSG_MIN_STAKE):
        cf.flip.approve(cf.stakeManager.address, MIN_STAKE - 1, {"from": cf.ALICE})
        cf.stakeManager.stake(
            JUNK_HEX, MIN_STAKE - 1, NON_ZERO_ADDR, {"from": cf.ALICE}
        )


def test_stake_rev_nodeID(cf):
    with reverts(REV_MSG_NZ_BYTES32):
        cf.stakeManager.stake(
            0, cf.stakeManager.getMinimumStake(), NON_ZERO_ADDR, {"from": cf.ALICE}
        )
