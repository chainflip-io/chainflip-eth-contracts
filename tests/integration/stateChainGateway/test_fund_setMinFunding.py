from consts import *
from shared_tests import *
from brownie import reverts, web3


def test_setMinFunding_fundStateChainAccount(cf):
    # Set new minimum funding
    newMinFunding = int(MIN_FUNDING * 1.5)
    setMinFundingTx = cf.stateChainGateway.setMinFunding(
        newMinFunding, {"from": cf.GOVERNOR}
    )

    # Check things that should've changed
    assert cf.stateChainGateway.getMinimumFunding() == newMinFunding
    assert setMinFundingTx.events["MinFundingChanged"][0].values() == [
        MIN_FUNDING,
        newMinFunding,
    ]
    # Check things that shouldn't have changed
    assert cf.flip.balanceOf(cf.stateChainGateway) == GATEWAY_INITIAL_BALANCE

    # Funding an amount valid for the last min but not the current min should revert
    with reverts(REV_MSG_MIN_FUNDING):
        cf.stateChainGateway.fundStateChainAccount(
            JUNK_HEX, MIN_FUNDING, {"from": cf.ALICE}
        )

    cf.flip.approve(cf.stateChainGateway.address, newMinFunding, {"from": cf.ALICE})
    fundTx = cf.stateChainGateway.fundStateChainAccount(
        JUNK_HEX, newMinFunding, {"from": cf.ALICE}
    )

    fundTest(cf, 0, JUNK_HEX, newMinFunding, fundTx, newMinFunding)
