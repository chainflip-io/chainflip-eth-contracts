from consts import *
from brownie import reverts
from brownie.test import given, strategy


@given(st_newMinStake=strategy("uint256", exclude=0))
def test_setMinStake(cf, st_newMinStake):
    tx = cf.stakeManager.setMinStake(st_newMinStake, {"from": cf.GOVERNOR})

    # Check things that should've changed
    assert cf.stakeManager.getMinimumStake() == st_newMinStake
    assert tx.events["MinStakeChanged"][0].values() == [MIN_STAKE, st_newMinStake]

    # Check things that shouldn't have changed
    assert cf.flip.balanceOf(cf.stakeManager) == STAKEMANAGER_INITIAL_BALANCE


def test_setMinStake_rev_amount(cf):
    with reverts(REV_MSG_NZ_UINT):
        cf.stakeManager.setMinStake(0, {"from": cf.GOVERNOR})


def test_setMinStake_rev_governor(cf):
    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.stakeManager.setMinStake(1, {"from": cf.ALICE})
