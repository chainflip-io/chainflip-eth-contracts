from consts import *
from shared_tests import *
from brownie import web3, chain
from utils import *


def test_registerClaim_updateFlipSupply_executeClaim(cf, stakedMin):
    _, amountStaked = stakedMin
    claimAmount = amountStaked
    receiver = cf.DENICE

    registerClaimTest(
        cf,
        cf.stakeManager,
        JUNK_HEX,
        MIN_STAKE,
        claimAmount,
        receiver,
        getChainTime() + (2 * CLAIM_DELAY),
    )

    stateChainBlockNumber = 1

    args = (NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber)
    tx = signed_call_cf(cf, cf.stakeManager.updateFlipSupply, *args, sender=cf.ALICE)

    # Check things that should've changed
    assert (
        cf.flip.balanceOf(cf.stakeManager)
        == amountStaked
        + NEW_TOTAL_SUPPLY_MINT
        - INIT_SUPPLY
        + STAKEMANAGER_INITIAL_BALANCE
    )
    assert cf.flip.totalSupply() == NEW_TOTAL_SUPPLY_MINT
    assert tx.events["FlipSupplyUpdated"][0].values() == [
        INIT_SUPPLY,
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    ]

    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE

    chain.sleep(CLAIM_DELAY + 5)
    cf.stakeManager.executeClaim(JUNK_HEX, {"from": cf.ALICE})

    # Check things that should've changed
    assert cf.stakeManager.getPendingClaim(JUNK_HEX) == NULL_CLAIM

    assert (
        cf.flip.balanceOf(cf.stakeManager)
        == amountStaked
        + (NEW_TOTAL_SUPPLY_MINT - INIT_SUPPLY + STAKEMANAGER_INITIAL_BALANCE)
        - claimAmount
    )
    assert cf.flip.balanceOf(receiver) == claimAmount
    assert cf.flip.totalSupply() == NEW_TOTAL_SUPPLY_MINT

    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE
