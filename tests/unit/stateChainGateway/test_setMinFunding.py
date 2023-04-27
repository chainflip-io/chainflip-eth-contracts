from consts import *
from brownie import reverts
from brownie.test import given, strategy


@given(st_newMinFunding=strategy("uint256", exclude=0))
def test_setMinFunding(cf, st_newMinFunding):
    tx = cf.stateChainGateway.setMinFunding(st_newMinFunding, {"from": cf.GOVERNOR})

    # Check things that should've changed
    assert cf.stateChainGateway.getMinimumFunding() == st_newMinFunding
    assert tx.events["MinFundingChanged"][0].values() == [MIN_FUNDING, st_newMinFunding]

    # Check things that shouldn't have changed
    assert cf.flip.balanceOf(cf.stateChainGateway) == GATEWAY_INITIAL_BALANCE


def test_setMinFunding_rev_amount(cf):
    with reverts(REV_MSG_NZ_UINT):
        cf.stateChainGateway.setMinFunding(0, {"from": cf.GOVERNOR})


def test_setMinFunding_rev_governor(cf):
    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.stateChainGateway.setMinFunding(1, {"from": cf.ALICE})
