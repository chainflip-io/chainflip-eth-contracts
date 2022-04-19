from consts import *
from brownie import reverts
from test_stake import test_stake_min


def test_govWithdraw(cf, stakedMin):
    # Test that governance can withdraw all the FLIP
    # First we should stake to make sure that there is something in there
    test_stake_min(cf, stakedMin)
    stakeManagerFlipBalance = cf.flip.balanceOf(cf.stakeManager)
    governorFlipBalance = cf.flip.balanceOf(cf.GOVERNOR)
    communityFlipBalance = cf.flip.balanceOf(cf.COMMUNITY_KEY)

    # Ensure that we're not dealing with zero
    assert stakeManagerFlipBalance != 0

    with reverts(REV_MSG_STAKEMAN_GOVERNOR):
        cf.stakeManager.govWithdraw({"from": cf.ALICE})

    with reverts(REV_MSG_COMMUNITY_GUARD):
        cf.stakeManager.govWithdraw({"from": cf.GOVERNOR})

    cf.stakeManager.setCommunityGuard(
        DISABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY}
    )

    with reverts(REV_MSG_STAKEMAN_NOT_SUSPENDED):
        cf.stakeManager.govWithdraw({"from": cf.GOVERNOR})

    cf.stakeManager.suspend({"from": cf.GOVERNOR})

    with reverts(REV_MSG_STAKEMAN_GOVERNOR):
        cf.stakeManager.govWithdraw({"from": cf.ALICE})

    tx = cf.stakeManager.govWithdraw({"from": cf.GOVERNOR})

    assert cf.flip.balanceOf(cf.stakeManager) == 0
    assert (
        cf.flip.balanceOf(cf.GOVERNOR) == stakeManagerFlipBalance + governorFlipBalance
    )
    assert cf.flip.balanceOf(cf.COMMUNITY_KEY) == communityFlipBalance
    assert tx.events["GovernanceWithdrawal"][0].values() == [
        cf.GOVERNOR,
        stakeManagerFlipBalance,
    ]
