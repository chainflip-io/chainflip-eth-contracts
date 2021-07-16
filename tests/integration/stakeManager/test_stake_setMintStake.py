from consts import *
from shared_tests import *
from brownie import reverts, web3


def test_setMinStake_stake(cf):
    # Set new minimum stake
    newMinStake = int(MIN_STAKE * 1.5)
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(gov_null_sig(), newMinStake)
    setMinStakeTx = cf.stakeManager.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig), newMinStake)

    # Check things that should've changed
    assert cf.stakeManager.getMinimumStake() == newMinStake
    assert setMinStakeTx.events["MinStakeChanged"][0].values() == [MIN_STAKE, newMinStake]
    # Check things that shouldn't have changed
    assert cf.flip.balanceOf(cf.stakeManager) == 0

    # Staking an amount valid for the last min but not the current min should revert
    with reverts(REV_MSG_MIN_STAKE):
        cf.stakeManager.stake(JUNK_HEX, MIN_STAKE, NON_ZERO_ADDR, cf.FR_ALICE)

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