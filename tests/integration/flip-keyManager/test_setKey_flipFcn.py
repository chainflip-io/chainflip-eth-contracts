from consts import *
from shared_tests import *
from brownie import reverts, web3


def test_setAggKeyWithAggKey_updateFlipSupply(cfAW):
    # Change agg keys
    setAggKeyWithAggKey_test(cfAW)

    stateChainBlockNumber = 1

    args = (NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber, cfAW.stakeManager.address)

    # Updating supply with old key should revert
    with reverts(REV_MSG_SIG):
        signed_call_cf(cfAW, cfAW.flip.updateFlipSupply, *args, sender=cfAW.ALICE)

    tx = signed_call_cf(
        cfAW, cfAW.flip.updateFlipSupply, *args, sender=cfAW.ALICE, signer=AGG_SIGNER_2
    )

    # Check things that should've changed
    assert cfAW.flip.totalSupply() == NEW_TOTAL_SUPPLY_MINT
    assert (
        cfAW.flip.balanceOf(cfAW.stakeManager)
        == NEW_TOTAL_SUPPLY_MINT - INIT_SUPPLY + STAKEMANAGER_INITIAL_BALANCE
    )
    assert cfAW.flip.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    assert tx.events["FlipSupplyUpdated"][0].values() == [
        INIT_SUPPLY,
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    ]

    # Check things that shouldn't have changed
    assert cfAW.stakeManager.getMinimumStake() == MIN_STAKE
