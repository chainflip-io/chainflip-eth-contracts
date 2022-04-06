from consts import *
from shared_tests import *
from brownie import reverts, web3


def test_setAggKeyWithAggKey_updateFlipSupply(cfAW):
    # Change agg keys
    setAggKeyWithAggKey_test(cfAW)

    stateChainBlockNumber = 1

    callDataNoSig = cfAW.flip.updateFlipSupply.encode_input(
        agg_null_sig(cfAW.keyManager.address, chain.id),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        cfAW.stakeManager.address,
    )

    # Updating supply with old key should revert
    with reverts(REV_MSG_SIG):
        cfAW.flip.updateFlipSupply(
            AGG_SIGNER_1.getSigData(callDataNoSig, cfAW.keyManager.address),
            NEW_TOTAL_SUPPLY_MINT,
            stateChainBlockNumber,
            cfAW.stakeManager.address,
            cfAW.FR_ALICE,
        )

    # Updating supply with new key
    callDataNoSig = cfAW.flip.updateFlipSupply.encode_input(
        agg_null_sig(cfAW.keyManager.address, chain.id),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        cfAW.stakeManager.address,
    )
    tx = cfAW.flip.updateFlipSupply(
        AGG_SIGNER_2.getSigData(callDataNoSig, cfAW.keyManager.address),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        cfAW.stakeManager.address,
        cfAW.FR_ALICE,
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
