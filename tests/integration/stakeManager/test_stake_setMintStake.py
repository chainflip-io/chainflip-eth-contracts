from consts import *
from shared_tests import *
from brownie import reverts, web3


def test_setMinStake_stake(cf):
    # Set new minimum stake
    newMinStake = int(MIN_STAKE * 1.5)
    setMinStakeTx = cf.stakeManager.setMinStake(newMinStake, {"from": cf.GOVERNOR})

    # Check things that should've changed
    assert cf.stakeManager.getMinimumStake() == newMinStake
    assert setMinStakeTx.events["MinStakeChanged"][0].values() == [MIN_STAKE, newMinStake]
    # Check things that shouldn't have changed
    assert cf.flip.balanceOf(cf.stakeManager) == STAKEMANAGER_INITIAL_BALANCE

    # Staking an amount valid for the last min but not the current min should revert
    with reverts(REV_MSG_MIN_STAKE):
        cf.stakeManager.stake(JUNK_HEX, MIN_STAKE, NON_ZERO_ADDR, cf.FR_ALICE)

    cf.flip.approve(cf.stakeManager.address, newMinStake, {'from': cf.ALICE})
    stakeTx = cf.stakeManager.stake(JUNK_HEX, newMinStake, NON_ZERO_ADDR, cf.FR_ALICE)

    stakeTest(
        cf,
        0,
        JUNK_HEX,
        newMinStake,
        stakeTx,
        newMinStake,
        NON_ZERO_ADDR
    )