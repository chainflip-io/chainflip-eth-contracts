from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
from utils import *


@given(st_amount=strategy("uint256", max_value=MAX_TEST_STAKE))
def test_stake_st_amount_rand(cf, st_amount):
    if st_amount < MIN_STAKE:
        with reverts(REV_MSG_MIN_STAKE):
            cf.flip.approve(cf.stakeManager.address, st_amount, {"from": cf.ALICE})
            cf.stakeManager.stake(
                JUNK_HEX, st_amount, NON_ZERO_ADDR, {"from": cf.ALICE}
            )
    else:
        cf.flip.approve(cf.stakeManager.address, st_amount, {"from": cf.ALICE})
        tx = cf.stakeManager.stake(
            JUNK_HEX, st_amount, NON_ZERO_ADDR, {"from": cf.ALICE}
        )
        stakeTest(cf, 0, JUNK_HEX, MIN_STAKE, tx, st_amount, NON_ZERO_ADDR)


def test_stake_min(cf, stakedMin):
    tx, amount = stakedMin
    stakeTest(cf, 0, JUNK_HEX, MIN_STAKE, tx, amount, NON_ZERO_ADDR)


def test_stake_rev_st_amount_just_under_minStake(cf):
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


def test_stake_rev_zaddr(cf):
    with reverts(REV_MSG_NZ_ADDR):
        cf.stakeManager.stake(
            JUNK_HEX, cf.stakeManager.getMinimumStake(), ZERO_ADDR, {"from": cf.ALICE}
        )
