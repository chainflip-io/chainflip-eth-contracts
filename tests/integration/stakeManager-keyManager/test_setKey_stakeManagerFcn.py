from consts import *
from shared_tests import *
from brownie import reverts, web3


def test_setGovKeyWithGovKey_setMinStake(cfAW):
    # Change agg keys
    setGovKeyWithGovKey_test(cfAW)

    newMinStake = int(MIN_STAKE * 1.5)

    # Changing emission with old key should revert
    with reverts(REV_MSG_STAKEMAN_GOVERNOR):
        cfAW.stakeManager.setMinStake(newMinStake, {"from": cfAW.GOVERNOR})

    # Change minStake with new key
    tx = cfAW.stakeManager.setMinStake(newMinStake, {"from": cfAW.GOVERNOR_2})

    # Check things that should've changed
    assert cfAW.stakeManager.getMinimumStake() == newMinStake
    assert tx.events["MinStakeChanged"][0].values() == [MIN_STAKE, newMinStake]

    # Check things that shouldn't have changed
    assert cfAW.flip.balanceOf(cfAW.stakeManager) == STAKEMANAGER_INITIAL_BALANCE
