from consts import *
from shared_tests import *
from brownie import reverts, web3


def test_setGovKeyWithGovKey_setMinStake(cfAW):
    # Change gov keys with Gov Key
    setGovKeyWithGovKey_test(cfAW)
    # Check that only new governor can set minStake
    setMinStake_newGov(cfAW)


def test_setGovKeyWithAggKey_setMinStake(cfAW):
    # Change gov keys with Agg Key
    setGovKeyWithAggKey_test(cfAW)
    # Check that only new governor can set minStake
    setMinStake_newGov(cfAW)


def setMinStake_newGov(cfAW):
    newMinStake = int(MIN_STAKE * 1.5)

    # Changing minStake with old key should revert
    with reverts(REV_MSG_GOV_GOVERNOR):
        cfAW.stakeManager.setMinStake(newMinStake, {"from": cfAW.GOVERNOR})

    # Change minStake with new key
    tx = cfAW.stakeManager.setMinStake(newMinStake, {"from": cfAW.GOVERNOR_2})

    # Check things that should've changed
    assert cfAW.stakeManager.getMinimumStake() == newMinStake
    assert tx.events["MinStakeChanged"][0].values() == [MIN_STAKE, newMinStake]

    # Check things that shouldn't have changed
    assert cfAW.flip.balanceOf(cfAW.stakeManager) == STAKEMANAGER_INITIAL_BALANCE
