from consts import *
from brownie import reverts
from test_fund import test_fund_min
from shared_tests import *


def test_govWithdraw(cf, fundedMin):
    # Test that governance can withdraw all the FLIP
    # First we should fund to make sure that there is something in there
    test_fund_min(cf, fundedMin)
    stateChainGatewayFlipBalance = cf.flip.balanceOf(cf.stateChainGateway)
    governorFlipBalance = cf.flip.balanceOf(cf.GOVERNOR)
    communityFlipBalance = cf.flip.balanceOf(cf.COMMUNITY_KEY)

    # Ensure that we're not dealing with zero
    assert stateChainGatewayFlipBalance != 0

    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.stateChainGateway.govWithdraw({"from": cf.ALICE})

    with reverts(REV_MSG_GOV_ENABLED_GUARD):
        cf.stateChainGateway.govWithdraw({"from": cf.GOVERNOR})

    cf.stateChainGateway.disableCommunityGuard({"from": cf.COMMUNITY_KEY})

    with reverts(REV_MSG_GOV_NOT_SUSPENDED):
        cf.stateChainGateway.govWithdraw({"from": cf.GOVERNOR})

    cf.stateChainGateway.suspend({"from": cf.GOVERNOR})

    # Ensure that an external address cannot withdraw funds after removing guard
    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.stateChainGateway.govWithdraw({"from": cf.ALICE})

    tx = cf.stateChainGateway.govWithdraw({"from": cf.GOVERNOR})

    assert cf.flip.balanceOf(cf.stateChainGateway) == 0
    assert (
        cf.flip.balanceOf(cf.GOVERNOR)
        == stateChainGatewayFlipBalance + governorFlipBalance
    )
    assert cf.flip.balanceOf(cf.COMMUNITY_KEY) == communityFlipBalance
    assert tx.events["GovernanceWithdrawal"][0].values() == [
        cf.GOVERNOR,
        stateChainGatewayFlipBalance,
    ]
    assert cf.flip.getIssuer() == cf.GOVERNOR


def test_govWithdraw_update_govwithdraw(cf, fundedMin):
    test_fund_min(cf, fundedMin)
    cf.stateChainGateway.suspend({"from": cf.GOVERNOR})
    cf.stateChainGateway.disableCommunityGuard({"from": cf.COMMUNITY_KEY})

    # If we mistakenly or purposely update do govUpdateFlipIssuer before govWithdraw
    cf.stateChainGateway.govUpdateFlipIssuer({"from": cf.GOVERNOR})

    cf.stateChainGateway.govWithdraw({"from": cf.GOVERNOR})


# Transfer the FLIP issuance powers (mimic new SCGateway or multisig) via aggKey, and
# then check that governance can still emergency withdraw
def test_govWithdraw_upgrade_govwithdraw(cf, fundedMin):
    test_fund_min(cf, fundedMin)

    # Using an arbitrary contract as th enew issuer
    signed_call_cf(
        cf,
        cf.stateChainGateway.updateFlipIssuer,
        cf.vault.address,
        True,
        sender=cf.BOB,
    )

    cf.stateChainGateway.suspend({"from": cf.GOVERNOR})
    cf.stateChainGateway.disableCommunityGuard({"from": cf.COMMUNITY_KEY})

    assert cf.flip.getIssuer() == cf.vault.address
    # This shouldn't revert even if the issuer is not the governor
    cf.stateChainGateway.govWithdraw({"from": cf.GOVERNOR})
