from consts import *
from brownie import reverts


def test_suspend_executeClaim(cf, claimRegistered):

    # Register a claim for the full amount staked
    _, claim = claimRegistered
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == claim
    maxValidAmount = cf.flip.balanceOf(cf.stakeManager)
    assert maxValidAmount != 0

    # Simulate time between registering and suspending
    chain.sleep(int(CLAIM_DELAY / 2))

    # Suspend the StakeManager contract
    cf.stakeManager.suspend({"from": cf.GOVERNOR})

    # Simulate remaining time
    chain.sleep(CLAIM_DELAY)

    # Test that attempting to execute the claim fails
    with reverts(REV_MSG_STAKEMAN_SUSPENDED):
        cf.stakeManager.executeClaim(JUNK_HEX)

    # Resume the StakeManager
    cf.stakeManager.resume({"from": cf.GOVERNOR})

    # Execute the claim
    tx = cf.stakeManager.executeClaim(JUNK_HEX)

    # Verify tx result
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == NULL_CLAIM
    assert cf.flip.balanceOf(cf.stakeManager) == maxValidAmount - claim[0]
    assert tx.events["ClaimExecuted"][0].values() == [JUNK_HEX, claim[0]]
    assert cf.flip.balanceOf(claim[1]) == claim[0]


def test_suspend_govWithdraw_executeClaim(cf, claimRegistered):
    # Register a claim for the full amount staked
    _, claim = claimRegistered
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == claim
    maxValidAmount = cf.flip.balanceOf(cf.stakeManager)
    assert maxValidAmount != 0

    # Simulate time between registering and suspending
    chain.sleep(int(CLAIM_DELAY / 2))

    # Suspend the StakeManager contract
    cf.stakeManager.suspend({"from": cf.GOVERNOR})

    # Simulate remaining time
    chain.sleep(CLAIM_DELAY)

    # Test that attempting to execute the claim fails
    with reverts(REV_MSG_STAKEMAN_SUSPENDED):
        cf.stakeManager.executeClaim(JUNK_HEX)

    # Withdraw FLIP via governance motion
    tx = cf.stakeManager.govWithdraw({"from": cf.GOVERNOR})
    assert cf.flip.balanceOf(cf.stakeManager) == 0
    # [to, amount]
    assert tx.events["GovernanceWithdrawal"][0].values() == [
        cf.GOVERNOR,
        maxValidAmount,
    ]

    # Sanity check that we're still suspended
    with reverts(REV_MSG_STAKEMAN_SUSPENDED):
        cf.stakeManager.executeClaim(JUNK_HEX)

    # Resume the StakeManager
    cf.stakeManager.resume({"from": cf.GOVERNOR})

    # Attempt the execution, should fail because of balance in the Stake Manager
    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        cf.stakeManager.executeClaim(JUNK_HEX)
