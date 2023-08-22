from consts import *
from shared_tests import *
from brownie import web3, chain
from utils import *


def test_registerRedemption_updateFlipSupply_executeRedemption(cf, fundedMin):
    _, amountFunded = fundedMin
    redemptionAmount = amountFunded
    receiver = cf.DENICE

    registerRedemptionTest(
        cf,
        cf.stateChainGateway,
        JUNK_HEX,
        MIN_FUNDING,
        redemptionAmount,
        receiver,
        getChainTime() + (2 * REDEMPTION_DELAY),
        cf.ALICE,
    )

    stateChainBlockNumber = 1

    args = (NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber)
    tx = signed_call_cf(
        cf, cf.stateChainGateway.updateFlipSupply, *args, sender=cf.ALICE
    )

    # Check things that should've changed
    assert (
        cf.flip.balanceOf(cf.stateChainGateway)
        == amountFunded + NEW_TOTAL_SUPPLY_MINT - INIT_SUPPLY + GATEWAY_INITIAL_BALANCE
    )
    assert cf.flip.totalSupply() == NEW_TOTAL_SUPPLY_MINT
    assert tx.events["FlipSupplyUpdated"][0].values() == [
        INIT_SUPPLY,
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    ]

    # Check things that shouldn't have changed
    assert cf.stateChainGateway.getMinimumFunding() == MIN_FUNDING

    chain.sleep(REDEMPTION_DELAY + 5)
    cf.stateChainGateway.executeRedemption(JUNK_HEX, {"from": cf.ALICE})

    # Check things that should've changed
    assert cf.stateChainGateway.getPendingRedemption(JUNK_HEX) == NULL_CLAIM

    assert (
        cf.flip.balanceOf(cf.stateChainGateway)
        == amountFunded
        + (NEW_TOTAL_SUPPLY_MINT - INIT_SUPPLY + GATEWAY_INITIAL_BALANCE)
        - redemptionAmount
    )
    assert cf.flip.balanceOf(receiver) == redemptionAmount
    assert cf.flip.totalSupply() == NEW_TOTAL_SUPPLY_MINT

    # Check things that shouldn't have changed
    assert cf.stateChainGateway.getMinimumFunding() == MIN_FUNDING
