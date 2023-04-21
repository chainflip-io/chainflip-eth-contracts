from consts import *
from shared_tests import *
from brownie import reverts, web3


def test_setAggKeyWithAggKey_updateFlipSupply(cf):
    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    stateChainBlockNumber = 1

    args = (NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber)

    # Updating supply with old key should revert
    with reverts(REV_MSG_SIG):
        signed_call_cf(cf, cf.stakeManager.updateFlipSupply, *args, sender=cf.ALICE)

    tx = signed_call_cf(
        cf,
        cf.stakeManager.updateFlipSupply,
        *args,
        sender=cf.ALICE,
        signer=AGG_SIGNER_2
    )

    # Check things that should've changed
    assert cf.flip.totalSupply() == NEW_TOTAL_SUPPLY_MINT
    assert (
        cf.flip.balanceOf(cf.stakeManager)
        == NEW_TOTAL_SUPPLY_MINT - INIT_SUPPLY + STAKEMANAGER_INITIAL_BALANCE
    )
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    assert tx.events["FlipSupplyUpdated"][0].values() == [
        INIT_SUPPLY,
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    ]

    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE
