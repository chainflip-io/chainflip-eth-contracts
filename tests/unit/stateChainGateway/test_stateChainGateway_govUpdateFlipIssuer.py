from consts import *
from brownie import reverts
from test_fund import test_fund_min


def test_govUpdateFlipIssuer(cf):
    # Test that governance can update the FLIP issuer
    assert cf.flip.getIssuer() == cf.stateChainGateway

    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.stateChainGateway.govUpdateFlipIssuer({"from": cf.ALICE})

    with reverts(REV_MSG_GOV_ENABLED_GUARD):
        cf.stateChainGateway.govUpdateFlipIssuer({"from": cf.GOVERNOR})

    cf.stateChainGateway.disableCommunityGuard({"from": cf.COMMUNITY_KEY})

    with reverts(REV_MSG_GOV_NOT_SUSPENDED):
        cf.stateChainGateway.govUpdateFlipIssuer({"from": cf.GOVERNOR})

    cf.stateChainGateway.suspend({"from": cf.GOVERNOR})

    # Ensure that an external address cannot withdraw funds after removing guard
    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.stateChainGateway.govUpdateFlipIssuer({"from": cf.ALICE})

    assert cf.flip.getIssuer() == cf.stateChainGateway
    tx = cf.stateChainGateway.govUpdateFlipIssuer({"from": cf.GOVERNOR})
    assert cf.flip.getIssuer() == cf.GOVERNOR

    assert tx.events["IssuerUpdated"][0].values() == [
        cf.stateChainGateway,
        cf.GOVERNOR,
    ]

    # Ensure that the governance address can now issue new FLIP
    cf.flip.mint(cf.stateChainGateway, 100, {"from": cf.GOVERNOR})

    # Ensure that the cf.stateChainGateway cannot update the issuer
    with reverts(REV_MSG_FLIP_ISSUER):
        cf.stateChainGateway.govUpdateFlipIssuer({"from": cf.GOVERNOR})
