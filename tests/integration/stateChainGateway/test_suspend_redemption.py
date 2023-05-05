from consts import *
from brownie import reverts
from brownie.test import given, strategy
from shared_tests import *


def test_suspend_executeRedemption(cf, redemptionRegistered):

    # Register a redemption for the full amount funded
    _, redemption = redemptionRegistered
    assert cf.stateChainGateway.getPendingRedemption(JUNK_HEX) == redemption
    maxValidAmount = cf.flip.balanceOf(cf.stateChainGateway)
    assert maxValidAmount != 0

    # Simulate time between registering and suspending
    chain.sleep(int(REDEMPTION_DELAY / 2))

    # Suspend the StateChainGateway contract
    cf.stateChainGateway.suspend({"from": cf.GOVERNOR})

    # Simulate remaining time
    chain.sleep(REDEMPTION_DELAY)

    # Test that attempting to execute the redemption fails
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.stateChainGateway.executeRedemption(JUNK_HEX, {"from": cf.ALICE})

    # Resume the StateChainGateway
    cf.stateChainGateway.resume({"from": cf.GOVERNOR})

    # Execute the redemption
    tx = cf.stateChainGateway.executeRedemption(JUNK_HEX, {"from": cf.ALICE})

    # Verify tx result
    assert cf.stateChainGateway.getPendingRedemption(JUNK_HEX) == NULL_CLAIM
    assert cf.flip.balanceOf(cf.stateChainGateway) == maxValidAmount - redemption[0]
    assert tx.events["RedemptionExecuted"][0].values() == [JUNK_HEX, redemption[0]]
    assert cf.flip.balanceOf(redemption[1]) == redemption[0]


def test_suspend_govWithdraw_executeRedemption(cf, redemptionRegistered):
    # Register a redemption for the full amount funded
    _, redemption = redemptionRegistered
    assert cf.stateChainGateway.getPendingRedemption(JUNK_HEX) == redemption
    maxValidAmount = cf.flip.balanceOf(cf.stateChainGateway)
    assert maxValidAmount != 0

    # Simulate time between registering and suspending
    chain.sleep(int(REDEMPTION_DELAY / 2))

    # Suspend the StateChainGateway contract
    cf.stateChainGateway.suspend({"from": cf.GOVERNOR})

    # Simulate remaining time
    chain.sleep(REDEMPTION_DELAY)

    # Test that attempting to execute the redemption fails
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.stateChainGateway.executeRedemption(JUNK_HEX, {"from": cf.ALICE})

    # Withdraw FLIP via governance motion
    with reverts(REV_MSG_GOV_ENABLED_GUARD):
        cf.stateChainGateway.govWithdraw({"from": cf.GOVERNOR})

    cf.stateChainGateway.disableCommunityGuard({"from": cf.COMMUNITY_KEY})
    tx = cf.stateChainGateway.govWithdraw({"from": cf.GOVERNOR})

    assert cf.flip.balanceOf(cf.stateChainGateway) == 0
    # [to, amount]
    assert tx.events["GovernanceWithdrawal"][0].values() == [
        cf.GOVERNOR,
        maxValidAmount,
    ]

    # Check that the isser can also be updated
    tx = cf.stateChainGateway.govUpdateFlipIssuer({"from": cf.GOVERNOR})
    assert cf.flip.issuer() == cf.GOVERNOR

    # Sanity check that we're still suspended
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.stateChainGateway.executeRedemption(JUNK_HEX, {"from": cf.ALICE})

    # Resume the StateChainGateway
    cf.stateChainGateway.resume({"from": cf.GOVERNOR})

    # Attempt the execution, should fail because of balance in the State Chain Gateway
    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        cf.stateChainGateway.executeRedemption(JUNK_HEX, {"from": cf.ALICE})


@given(st_native_amount=strategy("uint"))
def test_suspend_registerRedemption(cf, st_native_amount):

    # Suspend the StateChainGateway contract
    cf.stateChainGateway.suspend({"from": cf.GOVERNOR})

    with reverts(REV_MSG_GOV_SUSPENDED):
        args = (
            JUNK_HEX,
            st_native_amount,
            cf.DENICE,
            getChainTime() + REDEMPTION_DELAY,
        )
        signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args)
